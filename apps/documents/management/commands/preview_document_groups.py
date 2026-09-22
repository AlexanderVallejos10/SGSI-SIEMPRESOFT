import os
import re
import unicodedata
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand

from apps.documents.models import SourceArtifact


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

    # V2: normalizamos separadores antes de eliminar estados para
    # quitar correctamente _BORRADOR, -NO VIGENTE, etc.
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


def build_group_key(artifact):
    area = normalize_search(area_root(artifact.original_path))
    title = normalized_title(artifact.original_name)
    family = artifact.classification.family_hint
    return f"{area}|{family}|{title}"


class Command(BaseCommand):
    help = (
        "Previsualiza V2 la agrupación de documentos SGSI controlados. "
        "Distingue representaciones PDF/DOCX de conflictos reales."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--top",
            type=int,
            default=80,
            help="Cantidad máxima de grupos a mostrar.",
        )
        parser.add_argument(
            "--show-singletons",
            action="store_true",
            help="Incluye grupos con un solo artefacto.",
        )

    def handle(self, *args, **options):
        top = options["top"]
        show_singletons = options["show_singletons"]

        qs = (
            SourceArtifact.objects
            .select_related("classification", "source_package")
            .filter(
                duplicate_of__isnull=True,
                source_verified=True,
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

        artifacts = list(qs)
        groups = defaultdict(list)
        family_counts = Counter()
        lifecycle_counts = Counter()

        for artifact in artifacts:
            groups[build_group_key(artifact)].append(artifact)
            family_counts[artifact.classification.family_hint] += 1
            lifecycle_counts[artifact.classification.lifecycle_hint] += 1

        singleton_count = 0
        multi_explicit = 0
        true_conflict_count = 0
        representation_groups = 0
        no_version_artifacts = 0
        groups_with_no_version = 0

        rows = []

        for key, items in groups.items():
            if len(items) == 1:
                singleton_count += 1

            version_buckets = defaultdict(list)
            for item in items:
                version = extract_version(item.original_name)
                if not version:
                    no_version_artifacts += 1
                    version = "(sin version)"
                version_buckets[version].append(item)

            if "(sin version)" in version_buckets:
                groups_with_no_version += 1

            explicit_versions = {
                version
                for version in version_buckets
                if version != "(sin version)"
            }
            if len(explicit_versions) > 1:
                multi_explicit += 1

            conflicts = []
            representations = []

            for version, version_items in version_buckets.items():
                by_ext = defaultdict(list)
                for item in version_items:
                    by_ext[(item.extension or "").lower()].append(item)

                if len(by_ext) > 1:
                    representations.append(
                        (
                            version,
                            sorted(by_ext.keys()),
                            len(version_items),
                        )
                    )

                for ext, ext_items in by_ext.items():
                    checksums = {
                        item.checksum_sha256
                        for item in ext_items
                    }
                    if len(checksums) > 1:
                        conflicts.append(
                            (
                                version,
                                ext or "(sin extensión)",
                                len(ext_items),
                                len(checksums),
                            )
                        )

            if representations:
                representation_groups += 1
            if conflicts:
                true_conflict_count += 1

            first = items[0]
            rows.append(
                {
                    "family": first.classification.family_hint,
                    "area": area_root(first.original_path),
                    "title": display_title(first.original_name),
                    "items": items,
                    "versions": version_buckets,
                    "conflicts": conflicts,
                    "representations": representations,
                }
            )

        rows.sort(
            key=lambda row: (
                0 if row["conflicts"] else 1,
                0 if row["representations"] else 1,
                -len(row["items"]),
                row["family"],
                row["title"].casefold(),
            )
        )

        self.stdout.write("=== AGRUPACIÓN DOCUMENTAL SGSI V2 ===")
        self.stdout.write(
            f"Artefactos controlados seleccionados: {len(artifacts)}"
        )
        self.stdout.write(
            f"Identidades documentales estimadas: {len(groups)}"
        )
        self.stdout.write(
            f"Grupos con una sola fuente: {singleton_count}"
        )
        self.stdout.write(
            f"Grupos con múltiples versiones explícitas: {multi_explicit}"
        )
        self.stdout.write(
            f"Grupos con múltiples representaciones (ej. PDF+DOCX): "
            f"{representation_groups}"
        )
        self.stdout.write(
            f"Grupos con conflicto REAL misma versión+extensión/diferente SHA: "
            f"{true_conflict_count}"
        )
        self.stdout.write(
            f"Artefactos sin versión explícita: {no_version_artifacts}"
        )
        self.stdout.write(
            f"Grupos con al menos un artefacto sin versión: "
            f"{groups_with_no_version}"
        )

        self.stdout.write("")
        self.stdout.write("=== POR FAMILIA ===")
        for key, value in family_counts.most_common():
            self.stdout.write(f"{key}: {value}")

        self.stdout.write("")
        self.stdout.write("=== POR CICLO DE VIDA ===")
        for key, value in lifecycle_counts.most_common():
            self.stdout.write(f"{key}: {value}")

        self.stdout.write("")
        self.stdout.write(
            "=== CONFLICTOS REALES / REPRESENTACIONES ==="
        )

        shown = 0
        for row in rows:
            if (
                len(row["items"]) == 1
                and not show_singletons
                and not row["conflicts"]
                and not row["representations"]
            ):
                continue

            self.stdout.write(
                f"\nGRUPO | {row['family']} | {row['area']} | "
                f"{row['title']} | fuentes={len(row['items'])}"
            )

            for version, ext, occurrences, checksums in row["conflicts"]:
                self.stdout.write(
                    self.style.ERROR(
                        f"  CONFLICTO REAL | version={version} | "
                        f"ext={ext} | fuentes={occurrences} | "
                        f"SHA distintos={checksums}"
                    )
                )

            for version, exts, occurrences in row["representations"]:
                self.stdout.write(
                    self.style.WARNING(
                        f"  REPRESENTACIONES | version={version} | "
                        f"ext={','.join(exts)} | fuentes={occurrences}"
                    )
                )

            for version, version_items in sorted(
                row["versions"].items(),
                key=lambda pair: pair[0],
            ):
                for item in version_items:
                    self.stdout.write(
                        f"  {version:<14} | "
                        f"{(item.extension or '-'):>5} | "
                        f"{item.classification.lifecycle_hint:<15} | "
                        f"{item.code} | "
                        f"{item.original_name}"
                    )

            shown += 1
            if shown >= top:
                break

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Preview V2 finalizado sin modificar la base de datos."
            )
        )
