import hashlib
import os
import re
import unicodedata
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.documents.models import (
    Document,
    DocumentImportIssue,
    DocumentVersion,
    DocumentVersionRepresentation,
    Evidence,
    SourceArtifact,
)
from apps.documents.models_promotion import (
    ImportIssueType,
    RepresentationType,
)


CONTROLLED_FAMILIES = (
    "politica",
    "manual",
    "procedimiento",
    "instructivo",
    "guia",
    "estandar",
    "formato",
    "plantilla",
    "matriz",
)

ALLOWED_EXTENSIONS = {
    "pdf", "doc", "docx", "odt",
    "xlsx", "xls", "xlsm", "ods",
}

SGSI_RELEVANCE = ("nucleo_sgsi", "soporte_sgsi")

VERSION_PATTERNS = (
    re.compile(
        r"(?i)(?:^|[\s_\-])v(?:ers(?:i[oó]n)?)?\s*[_\-]?\s*"
        r"(\d+(?:[._]\d+){0,3})(?=$|[\s_\-])"
    ),
    re.compile(
        r"(?i)(?:^|[\s_\-])versi[oó]n\s*[:_\-]?\s*"
        r"(\d+(?:[._]\d+){0,3})(?=$|[\s_\-])"
    ),
)

LEADING_NUMBER = re.compile(r"^\s*\d{1,3}\s*(?:[-_.]|[\)\]])\s*")
COPY_SUFFIX = re.compile(r"\s*\(\d+\)\s*$")
SEPARATORS = re.compile(r"[\s_\-–—]+")
STATUS_WORDS = re.compile(
    r"(?i)(?:^|\s)("
    r"borrador(?:es)?|"
    r"no\s+vigente(?:s)?|"
    r"vigente(?:s)?|"
    r"obsoleto(?:s)?|"
    r"draft"
    r")(?:$|\s)"
)
NON_ALNUM = re.compile(r"[^0-9a-záéíóúüñ\s]+")


def normalize_unicode(value):
    return unicodedata.normalize("NFKC", value or "").strip()


def normalize_search(value):
    value = normalize_unicode(value).casefold()
    value = unicodedata.normalize("NFKD", value)
    return "".join(
        ch for ch in value if not unicodedata.combining(ch)
    )


def area_root(path):
    parts = [
        part.strip()
        for part in (path or "").replace("\\", "/").split("/")
        if part.strip()
    ]
    if not parts:
        return "(sin area)"
    return re.sub(r"^_+", "", parts[0]).strip()


def extract_version(name):
    stem = os.path.splitext(name or "")[0]
    for pattern in VERSION_PATTERNS:
        match = pattern.search(stem)
        if match:
            return match.group(1).replace("_", ".")
    return ""


def normalized_title(name):
    stem = os.path.splitext(name or "")[0]
    stem = normalize_unicode(stem)
    stem = COPY_SUFFIX.sub("", stem)
    stem = LEADING_NUMBER.sub("", stem)

    for pattern in VERSION_PATTERNS:
        stem = pattern.sub(" ", stem)

    stem = SEPARATORS.sub(" ", stem)
    stem = STATUS_WORDS.sub(" ", stem.casefold())
    stem = NON_ALNUM.sub(" ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()

    return normalize_search(stem)


def display_title(name):
    stem = os.path.splitext(name or "")[0]
    stem = COPY_SUFFIX.sub("", normalize_unicode(stem))
    stem = LEADING_NUMBER.sub("", stem)

    for pattern in VERSION_PATTERNS:
        stem = pattern.sub(" ", stem)

    stem = SEPARATORS.sub(" ", stem)
    stem = STATUS_WORDS.sub(" ", stem)
    stem = re.sub(r"\s+", " ", stem).strip(" ._-")

    return stem or os.path.splitext(name or "")[0]


def group_raw_key(artifact):
    area = normalize_search(area_root(artifact.original_path))
    title = normalized_title(artifact.original_name)
    family = artifact.classification.family_hint
    return f"{area}|{family}|{title}"


def identity_key(raw_key):
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def doc_code(identity):
    return f"DOC-{identity[:20].upper()}"


def issue_code(identity, version_label, extension):
    raw = f"{identity}|{version_label}|{extension}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"ISS-{digest[:20].upper()}"


def evidence_code(artifact):
    digest = hashlib.sha256(
        f"{artifact.code}|{artifact.checksum_sha256}".encode("utf-8")
    ).hexdigest()
    return f"EVD-{digest[:20].upper()}"


def status_from_lifecycle(lifecycle):
    return {
        "vigente": "active",
        "no_vigente": "obsolete",
        "borrador": "draft",
        "historico": "inactive",
        "sin_clasificar": None,
    }.get(lifecycle)


def representation_type(extension):
    ext = (extension or "").lower()
    if ext == "pdf":
        return RepresentationType.PUBLISHED_PDF
    if ext in {"doc", "docx", "odt"}:
        return RepresentationType.EDITABLE_SOURCE
    if ext in {"xlsx", "xls", "xlsm", "ods"}:
        return RepresentationType.SPREADSHEET
    if ext in {"ppt", "pptx", "odp"}:
        return RepresentationType.PRESENTATION
    return RepresentationType.OTHER


def primary_rank(artifact):
    ext = (artifact.extension or "").lower()
    rank = {
        "pdf": 0,
        "xlsx": 1,
        "xlsm": 2,
        "xls": 3,
        "ods": 4,
        "docx": 5,
        "doc": 6,
        "odt": 7,
    }.get(ext, 50)

    life_rank = {
        "vigente": 0,
        "sin_clasificar": 1,
        "no_vigente": 2,
        "borrador": 3,
        "historico": 4,
    }.get(artifact.classification.lifecycle_hint, 9)

    return (rank, life_rank, artifact.original_name.casefold())


def choose_title(items):
    titles = [display_title(item.original_name) for item in items]
    counts = Counter(titles)
    return sorted(
        counts.items(),
        key=lambda pair: (-pair[1], len(pair[0]), pair[0].casefold()),
    )[0][0]


def detect_conflicts(version_items):
    by_ext = defaultdict(list)
    for item in version_items:
        by_ext[(item.extension or "").lower()].append(item)

    conflicts = []
    for ext, ext_items in by_ext.items():
        checksums = {item.checksum_sha256 for item in ext_items}
        if len(checksums) > 1:
            conflicts.append((ext, ext_items))
    return conflicts


def version_sort_value(label):
    if label == "SIN-VERSION":
        return (-1,)
    try:
        return tuple(int(part) for part in label.split("."))
    except Exception:
        return (-1,)


class Command(BaseCommand):
    help = (
        "Promueve fuentes SGSI controladas a Document, DocumentVersion y "
        "representaciones; registra conflictos e importa evidencias. "
        "Por defecto solo previsualiza; use --apply para guardar."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Guarda la promoción en PostgreSQL.",
        )
        parser.add_argument(
            "--show-documents",
            action="store_true",
            help="Muestra una línea por documento/version.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        apply_changes = options["apply"]
        show_documents = options["show_documents"]

        controlled_qs = (
            SourceArtifact.objects
            .select_related("classification")
            .filter(
                duplicate_of__isnull=True,
                source_verified=True,
                classification__rule_version="2026.09-v2",
                classification__sgsi_relevance__in=SGSI_RELEVANCE,
                classification__family_hint__in=CONTROLLED_FAMILIES,
                extension__in=ALLOWED_EXTENSIONS,
            )
            .exclude(file="")
            .order_by(
                "classification__family_hint",
                "original_path",
                "original_name",
            )
        )

        groups = defaultdict(list)
        for artifact in controlled_qs:
            groups[group_raw_key(artifact)].append(artifact)

        evidence_qs = (
            SourceArtifact.objects
            .select_related("classification")
            .filter(
                duplicate_of__isnull=True,
                source_verified=True,
                classification__rule_version="2026.09-v2",
                classification__sgsi_relevance__in=SGSI_RELEVANCE,
                classification__is_evidence_candidate=True,
            )
            .exclude(file="")
        )

        preview_docs = 0
        preview_versions = 0
        preview_reps = 0
        preview_issues = 0
        preview_evidence = evidence_qs.count()

        created_docs = 0
        created_versions = 0
        created_reps = 0
        created_issues = 0
        created_evidence = 0

        self.stdout.write(
            f"Modo: {'APPLY' if apply_changes else 'PREVIEW'}"
        )
        self.stdout.write(
            f"Grupos documentales: {len(groups)}"
        )
        self.stdout.write(
            f"Evidencias candidatas: {preview_evidence}"
        )
        self.stdout.write("")

        for raw_key, items in sorted(groups.items()):
            identity = identity_key(raw_key)
            title = choose_title(items)
            area = area_root(items[0].original_path)
            family = items[0].classification.family_hint

            buckets = defaultdict(list)
            for item in items:
                label = extract_version(item.original_name) or "SIN-VERSION"
                buckets[label].append(item)

            clean_buckets = []
            group_has_active = False
            group_has_draft = False
            all_obsolete = True
            group_conflicts = []

            for label, version_items in buckets.items():
                conflicts = detect_conflicts(version_items)

                if conflicts:
                    group_conflicts.extend(
                        (label, ext, conflict_items)
                        for ext, conflict_items in conflicts
                    )
                    preview_issues += len(conflicts)
                    continue

                primary = sorted(version_items, key=primary_rank)[0]
                version_status = status_from_lifecycle(
                    primary.classification.lifecycle_hint
                )

                if version_status == "active":
                    group_has_active = True
                if version_status == "draft":
                    group_has_draft = True
                if version_status != "obsolete":
                    all_obsolete = False

                clean_buckets.append(
                    (label, version_items, primary, version_status)
                )

            if not clean_buckets and not group_conflicts:
                continue

            preview_docs += 1
            preview_versions += len(clean_buckets)
            preview_reps += sum(len(row[1]) for row in clean_buckets)

            document_status = None
            if group_has_active:
                document_status = "active"
            elif group_has_draft:
                document_status = "draft"
            elif clean_buckets and all_obsolete:
                document_status = "obsolete"

            if apply_changes:
                document, created = Document.objects.get_or_create(
                    source_identity_key=identity,
                    defaults={
                        "code": doc_code(identity),
                        "title": title[:255],
                        "category": area[:100],
                        "document_type": family[:100],
                        "management_system": "SGSI",
                        "owner": None,
                        "status": document_status,
                    },
                )

                if created:
                    created_docs += 1

                for label, ext, conflict_items in group_conflicts:
                    code = issue_code(identity, label, ext)
                    issue, issue_created = DocumentImportIssue.objects.get_or_create(
                        code=code,
                        defaults={
                            "issue_type": ImportIssueType.VERSION_CONFLICT,
                            "group_key": identity,
                            "version_label": label,
                            "title": title[:255],
                            "description": (
                                "Misma identidad documental, misma versión "
                                f"({label}) y misma extensión (.{ext}), "
                                "pero con SHA-256 distintos. La versión no "
                                "se promovió automáticamente."
                            ),
                            "document": document,
                        },
                    )
                    if issue.document_id is None:
                        issue.document = document
                        issue.save(update_fields=["document", "updated_at"])
                    issue.source_artifacts.set(conflict_items)
                    if issue_created:
                        created_issues += 1

                for label, version_items, primary, version_status in sorted(
                    clean_buckets,
                    key=lambda row: version_sort_value(row[0]),
                ):
                    version, version_created = DocumentVersion.objects.get_or_create(
                        document=document,
                        version=label,
                        defaults={
                            "file": primary.file.name,
                            "checksum_sha256": primary.checksum_sha256,
                            "source_artifact": primary,
                            "change_reason": (
                                "Importación trazable desde inventario maestro."
                            ),
                            "status": version_status,
                        },
                    )

                    if version_created:
                        created_versions += 1

                    version.representations.update(is_primary=False)

                    for artifact in version_items:
                        is_primary = artifact.pk == primary.pk
                        rep_type = representation_type(artifact.extension)

                        _, rep_created = (
                            DocumentVersionRepresentation.objects.update_or_create(
                                source_artifact=artifact,
                                defaults={
                                    "document_version": version,
                                    "representation_type": rep_type,
                                    "is_primary": is_primary,
                                    "notes": (
                                        "Representación importada desde "
                                        "SourceArtifact verificado."
                                    ),
                                },
                            )
                        )
                        if rep_created:
                            created_reps += 1

                    changed_fields = []
                    if version.file.name != primary.file.name:
                        version.file.name = primary.file.name
                        changed_fields.append("file")
                    if version.source_artifact_id != primary.id:
                        version.source_artifact = primary
                        changed_fields.append("source_artifact")
                    if version.checksum_sha256 != primary.checksum_sha256:
                        version.checksum_sha256 = primary.checksum_sha256
                        changed_fields.append("checksum_sha256")
                    if changed_fields:
                        version.save(
                            update_fields=changed_fields + ["updated_at"]
                        )

                if show_documents:
                    self.stdout.write(
                        f"DOCUMENT | {document.code} | {title} | "
                        f"versiones={len(clean_buckets)} | "
                        f"conflictos={len(group_conflicts)}"
                    )

        if apply_changes:
            for artifact in evidence_qs:
                evidence = Evidence.objects.filter(
                    source_artifact=artifact
                ).first()

                if evidence is None:
                    description_field = Evidence._meta.get_field("description")
                    source_field = Evidence._meta.get_field("source")

                    description_max = description_field.max_length or 255
                    source_max = source_field.max_length or 160

                    # La ruta completa ya queda preservada de forma íntegra en
                    # SourceArtifact.original_path. Evidence.source usa una
                    # referencia corta y estable para no exceder su varchar.
                    evidence_source = (
                        f"Inventario maestro / {artifact.code}"
                    )[:source_max]

                    Evidence.objects.create(
                        code=evidence_code(artifact),
                        description=artifact.original_name[:description_max],
                        source=evidence_source,
                        checksum_sha256=artifact.checksum_sha256,
                        source_artifact=artifact,
                    )
                    created_evidence += 1

        self.stdout.write("")
        self.stdout.write("=== RESUMEN ===")
        self.stdout.write(
            f"Documentos previstos: {preview_docs}"
        )
        self.stdout.write(
            f"Versiones limpias previstas: {preview_versions}"
        )
        self.stdout.write(
            f"Representaciones previstas: {preview_reps}"
        )
        self.stdout.write(
            f"Incidencias de conflicto previstas: {preview_issues}"
        )
        self.stdout.write(
            f"Evidencias previstas: {preview_evidence}"
        )

        if apply_changes:
            self.stdout.write("")
            self.stdout.write(
                f"Documentos creados en esta ejecución: {created_docs}"
            )
            self.stdout.write(
                f"Versiones creadas en esta ejecución: {created_versions}"
            )
            self.stdout.write(
                f"Representaciones creadas en esta ejecución: {created_reps}"
            )
            self.stdout.write(
                f"Incidencias creadas en esta ejecución: {created_issues}"
            )
            self.stdout.write(
                f"Evidencias creadas en esta ejecución: {created_evidence}"
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "Promoción documental finalizada."
                )
            )
        else:
            transaction.set_rollback(True)
            self.stdout.write(
                self.style.WARNING(
                    "PREVIEW: no se modificó PostgreSQL."
                )
            )
