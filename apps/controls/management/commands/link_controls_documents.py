import os
import re
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.controls.models import Control, ControlEvidence
from apps.controls.models_iso import ControlSupportReference
from apps.controls.models_linking import (
    ControlDocumentAssignment,
    ControlDocumentMatchMethod,
)
from apps.documents.models import Document, Evidence


RULE_VERSION = "2026.09-control-doc-v1"

VERSION_RE = re.compile(
    r"(?i)(?:^|[\s_\-])v(?:ers(?:i[oó]n)?)?\s*[_\-]?\s*"
    r"\d+(?:[._]\d+){0,3}(?=$|[\s_\-])"
)

DETAIL_MARKERS = (
    " numeral ",
    " numerales ",
    " apartado ",
    " apartados ",
    " item ",
    " ítem ",
    " seccion ",
    " sección ",
)

LEADING_NUMBER_RE = re.compile(
    r"^\s*\d{1,3}\s*(?:[-_.]|[\)\]])\s*"
)


def normalize(value):
    value = str(value or "")
    value = value.replace("_x0002_", " ")
    value = value.replace("–", "-").replace("—", "-")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        ch for ch in value
        if not unicodedata.combining(ch)
    )
    value = value.casefold()
    value = VERSION_RE.sub(" ", value)
    value = re.sub(r"[^a-z0-9\s\-]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def singular_token(token):
    if len(token) > 5 and token.endswith("es"):
        return token[:-2]
    if len(token) > 4 and token.endswith("s"):
        return token[:-1]
    return token


def token_signature(value):
    return {
        singular_token(token)
        for token in normalize(value).split()
        if len(token) >= 3
    }


def clean_fragment(value):
    normal = normalize(str(value or "").strip(" ,.;:-"))

    for marker in DETAIL_MARKERS:
        marker_n = normalize(marker)
        idx = normal.find(marker_n)
        if idx > 4:
            normal = normal[:idx].strip()

    normal = re.sub(
        r"\s+\d+(?:\.\d+)+(?:\s|$).*$",
        "",
        normal,
    ).strip()

    return normal


def split_fragments(value):
    text = str(value or "").replace("\r", "\n")
    fragments = []

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        for part in re.split(r"[;|•]+", line):
            part = part.strip(" ,.;:-")
            if part and part != "-":
                fragments.append(part)

    return fragments


def aliases_for_document(document):
    aliases = []

    def add(alias, source):
        normalized = normalize(alias)
        if len(normalized) < 10:
            return
        if len(normalized.split()) < 2:
            return
        aliases.append(
            {
                "raw": str(alias),
                "normalized": normalized,
                "source": source,
            }
        )

    add(document.title, "document_title")
    seen_artifacts = set()

    for version in document.versions.all():
        artifact = version.source_artifact
        if artifact and artifact.pk not in seen_artifacts:
            seen_artifacts.add(artifact.pk)
            add(
                os.path.splitext(artifact.original_name)[0],
                "primary_artifact",
            )

        for representation in version.representations.all():
            artifact = representation.source_artifact
            if artifact and artifact.pk not in seen_artifacts:
                seen_artifacts.add(artifact.pk)
                add(
                    os.path.splitext(artifact.original_name)[0],
                    "representation_artifact",
                )

    unique = {}
    for alias in aliases:
        unique.setdefault(alias["normalized"], alias)

    return list(unique.values())


def exact_matches(reference_text, document_aliases):
    normalized_reference = normalize(reference_text)
    matches = {}

    for document, aliases in document_aliases.items():
        best = None

        for alias in aliases:
            candidate = alias["normalized"]

            if candidate in normalized_reference:
                confidence = (
                    99
                    if alias["source"] == "document_title"
                    else 97
                )

                item = {
                    "document": document,
                    "method": ControlDocumentMatchMethod.EXACT_REFERENCE,
                    "confidence": confidence,
                    "matched_alias": alias["raw"],
                    "matched_fragment": reference_text,
                    "reason": (
                        "El título/nombre fuente normalizado aparece "
                        "textualmente en la referencia del control."
                    ),
                }

                if best is None or confidence > best["confidence"]:
                    best = item

        if best:
            matches[document.pk] = best

    return matches


def fuzzy_matches(reference_text, document_aliases, already_matched, min_confidence):
    matches = {}

    for fragment in split_fragments(reference_text):
        fragment_clean = clean_fragment(fragment)
        fragment_tokens = token_signature(fragment_clean)

        if len(fragment_clean) < 10 or len(fragment_tokens) < 2:
            continue

        candidates = []

        for document, aliases in document_aliases.items():
            if document.pk in already_matched:
                continue

            for alias in aliases:
                alias_norm = alias["normalized"]
                alias_tokens = token_signature(alias_norm)

                if not alias_tokens:
                    continue

                overlap = len(
                    alias_tokens & fragment_tokens
                ) / max(len(alias_tokens), 1)

                prefix = fragment_clean[:len(alias_norm) + 12]
                ratio = SequenceMatcher(
                    None,
                    alias_norm,
                    prefix,
                ).ratio()

                full_ratio = SequenceMatcher(
                    None,
                    alias_norm,
                    fragment_clean,
                ).ratio()

                score = max(ratio, full_ratio)

                if score >= 0.90 or (
                    score >= 0.82 and overlap >= 0.80
                ):
                    confidence = min(
                        95,
                        max(
                            86,
                            round(
                                (
                                    score * 0.65
                                    + overlap * 0.35
                                )
                                * 100
                            ),
                        ),
                    )

                    if confidence >= min_confidence:
                        candidates.append(
                            {
                                "document": document,
                                "method": ControlDocumentMatchMethod.FUZZY_REFERENCE,
                                "confidence": confidence,
                                "matched_alias": alias["raw"],
                                "matched_fragment": fragment,
                                "reason": (
                                    "Coincidencia normalizada de alta similitud "
                                    "entre referencia del control y título/nombre "
                                    "fuente del documento."
                                ),
                                "score": score,
                                "overlap": overlap,
                            }
                        )

        if not candidates:
            continue

        candidates.sort(
            key=lambda item: (
                item["confidence"],
                item["score"],
                item["overlap"],
            ),
            reverse=True,
        )

        best = candidates[0]
        second = candidates[1] if len(candidates) > 1 else None

        if second and (
            best["confidence"] - second["confidence"] < 4
            and best["document"].pk != second["document"].pk
        ):
            continue

        existing = matches.get(best["document"].pk)
        if (
            existing is None
            or best["confidence"] > existing["confidence"]
        ):
            matches[best["document"].pk] = best

    return matches


def document_source_artifact_ids(document):
    ids = set()

    for version in document.versions.all():
        if version.source_artifact_id:
            ids.add(version.source_artifact_id)

        for representation in version.representations.all():
            if representation.source_artifact_id:
                ids.add(representation.source_artifact_id)

    return ids


class Command(BaseCommand):
    help = (
        "Vincula los 93 controles ISO con documentos reales usando las "
        "referencias de VerificacionNorma.xlsx. Propone/crea "
        "ControlEvidence solo cuando documento y Evidence comparten "
        "exactamente el mismo SourceArtifact. Por defecto es PREVIEW."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Guarda las vinculaciones.",
        )
        parser.add_argument(
            "--show-unmatched",
            action="store_true",
            help="Muestra controles sin documentos vinculables.",
        )
        parser.add_argument(
            "--show-links",
            action="store_true",
            help="Muestra las vinculaciones propuestas.",
        )
        parser.add_argument(
            "--min-fuzzy-confidence",
            type=int,
            default=95,
            help=(
                "Confianza mínima para conservar una relación fuzzy. "
                "Por defecto: 95."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        apply_changes = options["apply"]
        show_unmatched = options["show_unmatched"]
        show_links = options["show_links"]
        min_fuzzy_confidence = options["min_fuzzy_confidence"]

        if not 0 <= min_fuzzy_confidence <= 100:
            raise ValueError(
                "--min-fuzzy-confidence debe estar entre 0 y 100."
            )

        documents = (
            Document.objects
            .prefetch_related(
                "versions__source_artifact",
                "versions__representations__source_artifact",
            )
            .order_by("code")
        )

        references = (
            ControlSupportReference.objects
            .select_related("control")
            .order_by("control__code")
        )

        document_aliases = {
            document: aliases_for_document(document)
            for document in documents
        }

        control_matches = defaultdict(dict)
        unmatched_controls = []
        method_counter = Counter()

        for reference in references:
            exact = exact_matches(
                reference.supporting_reference,
                document_aliases,
            )

            fuzzy = fuzzy_matches(
                reference.supporting_reference,
                document_aliases,
                already_matched=set(exact),
                min_confidence=min_fuzzy_confidence,
            )

            merged = dict(exact)
            merged.update(fuzzy)

            if not merged:
                unmatched_controls.append(reference.control)
                continue

            for document_id, match in merged.items():
                match["support_reference"] = reference
                control_matches[reference.control_id][document_id] = match
                method_counter[match["method"]] += 1

        predicted_assignments = sum(
            len(items)
            for items in control_matches.values()
        )

        evidence_by_artifact = {
            evidence.source_artifact_id: evidence
            for evidence in Evidence.objects.filter(
                source_artifact__isnull=False
            )
        }

        predicted_evidence_links = set()

        for control_id, matches in control_matches.items():
            for match in matches.values():
                artifact_ids = document_source_artifact_ids(
                    match["document"]
                )

                for artifact_id in artifact_ids:
                    evidence = evidence_by_artifact.get(artifact_id)
                    if evidence:
                        predicted_evidence_links.add(
                            (control_id, evidence.pk)
                        )

        controls_by_id = {
            control.id: control
            for control in Control.objects.all()
        }

        if show_links:
            self.stdout.write("=== VINCULACIONES PROPUESTAS ===")

            for control_id, matches in sorted(
                control_matches.items(),
                key=lambda pair: controls_by_id[pair[0]].code,
            ):
                control = controls_by_id[control_id]

                for match in sorted(
                    matches.values(),
                    key=lambda item: (
                        -item["confidence"],
                        item["document"].code,
                    ),
                ):
                    self.stdout.write(
                        f"{control.code} | "
                        f"{match['confidence']}% | "
                        f"{match['method']} | "
                        f"{match['document'].title}"
                    )

        if show_unmatched and unmatched_controls:
            self.stdout.write("")
            self.stdout.write("=== CONTROLES SIN DOCUMENTO ===")
            for control in unmatched_controls:
                self.stdout.write(
                    f"{control.code} | {control.name}"
                )

        if apply_changes:
            ControlDocumentAssignment.objects.exclude(
                method=ControlDocumentMatchMethod.MANUAL
            ).update(is_active=False)

            for control_id, matches in control_matches.items():
                control = controls_by_id[control_id]

                for match in matches.values():
                    reference = match["support_reference"]

                    ControlDocumentAssignment.objects.update_or_create(
                        control=control,
                        document=match["document"],
                        defaults={
                            "support_reference": reference,
                            "method": match["method"],
                            "confidence": match["confidence"],
                            "matched_fragment": match["matched_fragment"],
                            "matched_alias": match["matched_alias"][:255],
                            "reason": match["reason"],
                            "rule_version": RULE_VERSION,
                            "is_active": True,
                        },
                    )

            for control in Control.objects.all():
                active_docs = Document.objects.filter(
                    control_assignments__control=control,
                    control_assignments__is_active=True,
                ).distinct()
                control.documents.set(active_docs)

            for control_id, evidence_id in predicted_evidence_links:
                ControlEvidence.objects.get_or_create(
                    control_id=control_id,
                    evidence_id=evidence_id,
                    period="",
                    defaults={
                        "notes": (
                            "[AUTO-SOURCE-ARTIFACT "
                            f"{RULE_VERSION}] Documento y evidencia "
                            "comparten exactamente el mismo SourceArtifact. "
                            "Vinculación técnica pendiente de validación "
                            "funcional."
                        )
                    },
                )

        self.stdout.write("=== CONTROL ↔ DOCUMENTO / EVIDENCIA ===")
        self.stdout.write(
            f"Modo: {'APPLY' if apply_changes else 'PREVIEW'}"
        )
        self.stdout.write(
            f"Controles analizados: {references.count()}"
        )
        self.stdout.write(
            f"Documentos disponibles: {documents.count()}"
        )
        self.stdout.write(
            f"Controles con al menos un documento: {len(control_matches)}"
        )
        self.stdout.write(
            f"Controles sin documento automático: {len(unmatched_controls)}"
        )
        self.stdout.write(
            f"Asignaciones Control↔Document previstas: "
            f"{predicted_assignments}"
        )
        self.stdout.write(
            f"  exact_reference: "
            f"{method_counter[ControlDocumentMatchMethod.EXACT_REFERENCE]}"
        )
        self.stdout.write(
            f"  fuzzy_reference: "
            f"{method_counter[ControlDocumentMatchMethod.FUZZY_REFERENCE]}"
        )
        self.stdout.write(
            f"ControlEvidence exactas previstas: "
            f"{len(predicted_evidence_links)}"
        )
        self.stdout.write(
            f"Fuzzy mínimo: {min_fuzzy_confidence}%"
        )
        self.stdout.write(
            f"Regla: {RULE_VERSION}"
        )

        if not apply_changes:
            transaction.set_rollback(True)
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "PREVIEW: no se modificó PostgreSQL."
                )
            )
        else:
            self.stdout.write("")
            self.stdout.write(
                f"Assignments activos: "
                f"{ControlDocumentAssignment.objects.filter(is_active=True).count()}"
            )
            self.stdout.write(
                f"ControlEvidence totales: "
                f"{ControlEvidence.objects.count()}"
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "Vinculación Control↔Documento/Evidencia finalizada."
                )
            )
