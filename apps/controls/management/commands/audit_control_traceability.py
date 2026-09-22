import os
import re
import unicodedata
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.controls.models import ControlEvidence
from apps.controls.models_iso import ControlSupportReference
from apps.controls.models_linking import (
    ControlDocumentAssignment,
    ControlDocumentMatchMethod,
)
from apps.documents.models import Evidence


AUTO_NOTE_PREFIX = "[AUTO-EXACT-REFERENCE 2026.09-evidence-v1]"


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
    value = re.sub(r"[^a-z0-9\s\-]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def evidence_aliases(evidence):
    aliases = []

    def add(value):
        value = str(value or "").strip()
        if not value:
            return
        stem = os.path.splitext(os.path.basename(value))[0]
        norm = normalize(stem)
        if len(norm) < 18:
            return
        if len(norm.split()) < 3:
            return
        aliases.append((value, norm))

    add(evidence.description)

    if evidence.source_artifact_id:
        add(evidence.source_artifact.original_name)
        add(evidence.source_artifact.original_path)

    unique = {}
    for raw, norm in aliases:
        unique.setdefault(norm, raw)
    return [(raw, norm) for norm, raw in unique.items()]


class Command(BaseCommand):
    help = (
        "Audita la calidad de las relaciones Control↔Document y "
        "previsualiza vinculaciones ControlEvidence estrictas basadas "
        "en coincidencia textual exacta de nombres de evidencia. "
        "No modifica datos salvo que se use --apply-evidence."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--show-fuzzy",
            action="store_true",
            help="Muestra asignaciones fuzzy de confianza menor a 92.",
        )
        parser.add_argument(
            "--show-heavy",
            action="store_true",
            help="Muestra controles/documentos con muchas relaciones.",
        )
        parser.add_argument(
            "--show-evidence",
            action="store_true",
            help="Muestra evidencias exactas candidatas.",
        )
        parser.add_argument(
            "--apply-evidence",
            action="store_true",
            help=(
                "Crea únicamente ControlEvidence con coincidencia exacta "
                "de nombre entre referencia de control y evidencia."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        show_fuzzy = options["show_fuzzy"]
        show_heavy = options["show_heavy"]
        show_evidence = options["show_evidence"]
        apply_evidence = options["apply_evidence"]

        assignments = (
            ControlDocumentAssignment.objects
            .filter(is_active=True)
            .select_related("control", "document", "support_reference")
        )

        method_counts = Counter(
            assignments.values_list("method", flat=True)
        )

        controls_covered = (
            assignments.values("control_id").distinct().count()
        )
        documents_covered = (
            assignments.values("document_id").distinct().count()
        )

        confidence_bands = {
            "99-100": assignments.filter(confidence__gte=99).count(),
            "95-98": assignments.filter(
                confidence__gte=95,
                confidence__lte=98,
            ).count(),
            "92-94": assignments.filter(
                confidence__gte=92,
                confidence__lte=94,
            ).count(),
            "90-91": assignments.filter(
                confidence__gte=90,
                confidence__lte=91,
            ).count(),
            "<90": assignments.filter(confidence__lt=90).count(),
        }

        per_control = Counter(
            assignments.values_list("control__code", flat=True)
        )
        per_document = Counter(
            assignments.values_list("document__code", flat=True)
        )

        low_fuzzy = (
            assignments
            .filter(
                method=ControlDocumentMatchMethod.FUZZY_REFERENCE,
                confidence__lt=92,
            )
            .order_by("confidence", "control__code", "document__code")
        )

        references = list(
            ControlSupportReference.objects
            .select_related("control")
            .order_by("control__code")
        )

        evidences = list(
            Evidence.objects
            .select_related("source_artifact")
            .filter(source_artifact__isnull=False)
        )

        evidence_alias_map = {
            evidence.pk: evidence_aliases(evidence)
            for evidence in evidences
        }

        evidence_candidates = {}

        for reference in references:
            ref_norm = normalize(reference.supporting_reference)

            if not ref_norm:
                continue

            for evidence in evidences:
                aliases = evidence_alias_map[evidence.pk]

                for raw_alias, alias_norm in aliases:
                    if alias_norm in ref_norm:
                        key = (reference.control_id, evidence.pk)
                        current = evidence_candidates.get(key)

                        candidate = {
                            "control": reference.control,
                            "evidence": evidence,
                            "alias": raw_alias,
                            "reference": reference,
                        }

                        if current is None or len(alias_norm) > len(
                            normalize(current["alias"])
                        ):
                            evidence_candidates[key] = candidate
                        break

        existing_pairs = set(
            ControlEvidence.objects.values_list(
                "control_id",
                "evidence_id",
            )
        )

        new_candidates = {
            key: value
            for key, value in evidence_candidates.items()
            if key not in existing_pairs
        }

        created = 0

        if apply_evidence:
            for (control_id, evidence_id), item in new_candidates.items():
                _, was_created = ControlEvidence.objects.get_or_create(
                    control_id=control_id,
                    evidence_id=evidence_id,
                    period="",
                    defaults={
                        "notes": (
                            f"{AUTO_NOTE_PREFIX} Coincidencia textual exacta "
                            "del nombre de la evidencia dentro de la referencia "
                            "documental del control. Requiere validación "
                            "funcional antes de considerarse evidencia "
                            "confirmada de cumplimiento."
                        )
                    },
                )
                if was_created:
                    created += 1

        self.stdout.write("=== QA CONTROL ↔ DOCUMENTO ===")
        self.stdout.write(
            f"Assignments activos: {assignments.count()}"
        )
        self.stdout.write(
            f"Controles cubiertos: {controls_covered}"
        )
        self.stdout.write(
            f"Documentos vinculados: {documents_covered}"
        )
        self.stdout.write(
            "Métodos: "
            f"exact={method_counts[ControlDocumentMatchMethod.EXACT_REFERENCE]} "
            f"| fuzzy={method_counts[ControlDocumentMatchMethod.FUZZY_REFERENCE]} "
            f"| manual={method_counts[ControlDocumentMatchMethod.MANUAL]}"
        )

        self.stdout.write("")
        self.stdout.write("Confianza:")
        for band, count in confidence_bands.items():
            self.stdout.write(
                f"  {band}: {count}"
            )

        heavy_controls = [
            (code, count)
            for code, count in per_control.most_common()
            if count >= 6
        ]
        heavy_documents = [
            (code, count)
            for code, count in per_document.most_common()
            if count >= 10
        ]

        self.stdout.write("")
        self.stdout.write(
            f"Fuzzy <92% para revisión: {low_fuzzy.count()}"
        )
        self.stdout.write(
            f"Controles con >=6 documentos: {len(heavy_controls)}"
        )
        self.stdout.write(
            f"Documentos vinculados a >=10 controles: "
            f"{len(heavy_documents)}"
        )

        if show_fuzzy and low_fuzzy.exists():
            self.stdout.write("")
            self.stdout.write("=== FUZZY <92% ===")
            for assignment in low_fuzzy:
                self.stdout.write(
                    f"{assignment.control.code} | "
                    f"{assignment.confidence}% | "
                    f"{assignment.document.code} | "
                    f"{assignment.document.title}"
                )

        if show_heavy:
            if heavy_controls:
                self.stdout.write("")
                self.stdout.write("=== CONTROLES CON MUCHOS DOCUMENTOS ===")
                for code, count in heavy_controls:
                    self.stdout.write(
                        f"{code} | documentos={count}"
                    )

            if heavy_documents:
                self.stdout.write("")
                self.stdout.write("=== DOCUMENTOS EN MUCHOS CONTROLES ===")
                by_code = {
                    assignment.document.code: assignment.document.title
                    for assignment in assignments
                    if assignment.document.code in dict(heavy_documents)
                }
                for code, count in heavy_documents:
                    self.stdout.write(
                        f"{code} | controles={count} | "
                        f"{by_code.get(code, '')}"
                    )

        self.stdout.write("")
        self.stdout.write("=== EVIDENCIA EXACTA ===")
        self.stdout.write(
            f"Evidencias disponibles: {len(evidences)}"
        )
        self.stdout.write(
            f"Pares exactos Control↔Evidence detectados: "
            f"{len(evidence_candidates)}"
        )
        self.stdout.write(
            f"Pares nuevos: {len(new_candidates)}"
        )
        self.stdout.write(
            f"ControlEvidence existentes: {len(existing_pairs)}"
        )

        if show_evidence and evidence_candidates:
            self.stdout.write("")
            self.stdout.write("=== CANDIDATAS DE EVIDENCIA ===")
            for item in sorted(
                evidence_candidates.values(),
                key=lambda x: (
                    x["control"].code,
                    x["evidence"].code,
                ),
            ):
                self.stdout.write(
                    f"{item['control'].code} | "
                    f"{item['evidence'].code} | "
                    f"{item['evidence'].description}"
                )

        if apply_evidence:
            self.stdout.write("")
            self.stdout.write(
                f"ControlEvidence creadas en esta ejecución: {created}"
            )
            self.stdout.write(
                f"ControlEvidence totales: "
                f"{ControlEvidence.objects.count()}"
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "QA completado y evidencia exacta aplicada."
                )
            )
        else:
            transaction.set_rollback(True)
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "PREVIEW: no se modificó PostgreSQL."
                )
            )
