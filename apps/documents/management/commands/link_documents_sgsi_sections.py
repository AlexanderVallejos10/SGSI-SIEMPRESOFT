import unicodedata
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.documents.models import (
    Document,
    DocumentSectionAssignment,
    SGSISection,
)
from apps.documents.models_mapping import SectionAssignmentMethod


RULE_VERSION = "2026.09-section-v1"


def normalize(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(
        ch for ch in value
        if not unicodedata.combining(ch)
    )
    return value.casefold()


def document_text(document):
    chunks = [
        document.code or "",
        document.title or "",
        document.category or "",
        document.document_type or "",
    ]

    for version in document.versions.select_related(
        "source_artifact"
    ).all():
        artifact = version.source_artifact
        if artifact:
            chunks.extend(
                [
                    artifact.original_name or "",
                    artifact.original_path or "",
                ]
            )

    return normalize(" ".join(chunks))


def add_hit(hits, code, confidence, reason):
    current = hits.get(code)
    candidate = {
        "confidence": confidence,
        "reason": reason,
    }

    if current is None or confidence > current["confidence"]:
        hits[code] = candidate
    elif confidence == current["confidence"]:
        if reason not in current["reason"]:
            current["reason"] += " | " + reason


def infer_sections(document):
    text = document_text(document)
    family = normalize(document.document_type)
    hits = {}

    family_rules = {
        "politica": (
            "3.1",
            92,
            "La familia documental es política.",
        ),
        "procedimiento": (
            "3.2",
            92,
            "La familia documental es procedimiento.",
        ),
        "estandar": (
            "3.3",
            92,
            "La familia documental es estándar.",
        ),
        "instructivo": (
            "3.4",
            92,
            "La familia documental es instructivo/guía.",
        ),
        "guia": (
            "3.4",
            92,
            "La familia documental es instructivo/guía.",
        ),
        "manual": (
            "3",
            78,
            "La familia documental es manual del marco documental.",
        ),
        "formato": (
            "7.5",
            72,
            "Formato considerado información documentada.",
        ),
        "plantilla": (
            "7.5",
            72,
            "Plantilla considerada información documentada.",
        ),
    }

    if family in family_rules:
        code, confidence, reason = family_rules[family]
        add_hit(hits, code, confidence, reason)

    keyword_rules = [
        (
            ("contexto", "foda", "mision", "organigrama"),
            "4.1",
            90,
            "Contenido relacionado con contexto/organización.",
        ),
        (
            ("partes interesadas", "parte interesada"),
            "4.2",
            95,
            "Contenido relacionado con partes interesadas.",
        ),
        (
            ("alcance del sgsi", "alcance sgsi", "alcance de seguridad"),
            "4.3",
            96,
            "Contenido relacionado con alcance del SGSI.",
        ),
        (
            ("mapa de procesos", "sistema de gestion de seguridad"),
            "4.4",
            86,
            "Contenido relacionado con establecimiento/mantenimiento del SGSI.",
        ),
        (
            ("liderazgo", "compromiso de la direccion"),
            "5.1",
            90,
            "Contenido relacionado con liderazgo y compromiso.",
        ),
        (
            ("politica de seguridad de la informacion",),
            "5.2",
            99,
            "Política explícita de seguridad de la información.",
        ),
        (
            (
                "roles y responsabilidades",
                "roles responsabilidades",
                "responsabilidades y autoridades",
                "responsabilidades y autoridad",
                "comision para la destruccion",
            ),
            "5.3",
            88,
            "Contenido relacionado con roles, autoridades o responsabilidades.",
        ),
        (
            (
                "riesgos y oportunidades",
                "gestion de riesgos",
                "gestion del riesgo",
                "metodologia de riesgos",
                "metodologia de riesgo",
            ),
            "6.1",
            94,
            "Contenido relacionado con riesgos y oportunidades.",
        ),
        (
            (
                "objetivos de seguridad",
                "objetivos sgsi",
                "objetivos de la seguridad",
            ),
            "6.2",
            96,
            "Contenido relacionado con objetivos del SGSI.",
        ),
        (
            (
                "gestion de cambios",
                "control de cambios",
                "cambio critico",
            ),
            "6.3",
            88,
            "Contenido relacionado con planificación de cambios.",
        ),
        (
            ("recursos del sgsi", "recursos sgsi"),
            "7.1",
            88,
            "Contenido relacionado con recursos del SGSI.",
        ),
        (
            ("competencia", "capacitacion", "formacion"),
            "7.2",
            86,
            "Contenido relacionado con competencia/capacitación.",
        ),
        (
            (
                "concientizacion",
                "concienciacion",
                "conciencia de seguridad",
            ),
            "7.3",
            90,
            "Contenido relacionado con concienciación.",
        ),
        (
            (
                "comunicacion",
                "numeros para emergencias",
                "grupos especiales de interes",
            ),
            "7.4",
            82,
            "Contenido relacionado con comunicación.",
        ),
        (
            (
                "control de documentos",
                "documentos y registros",
                "control documental",
            ),
            "7.5",
            99,
            "Contenido explícito de control de información documentada.",
        ),
        (
            (
                "control operacional",
                "procedimientos operativos",
                "operacion del sgsi",
            ),
            "8.1",
            90,
            "Contenido relacionado con planificación/control operacional.",
        ),
        (
            (
                "evaluacion de riesgos",
                "evaluacion del riesgo",
                "matriz de riesgos",
                "matriz de riesgo",
            ),
            "8.2",
            95,
            "Contenido relacionado con evaluación de riesgos.",
        ),
        (
            (
                "tratamiento de riesgos",
                "tratamiento del riesgo",
                "plan de tratamiento",
            ),
            "8.3",
            95,
            "Contenido relacionado con tratamiento de riesgos.",
        ),
        (
            (
                "dashboard sgsi",
                "rendimiento sgsi",
                "indicadores sgsi",
                "monitoreo",
                "medicion",
            ),
            "9.1",
            94,
            "Contenido relacionado con monitoreo, medición o desempeño.",
        ),
        (
            ("auditoria interna", "auditoria del sgsi"),
            "9.2",
            96,
            "Contenido relacionado con auditoría interna.",
        ),
        (
            (
                "revision por la direccion",
                "revision de la gerencia",
                "revision gerencial",
            ),
            "9.3",
            96,
            "Contenido relacionado con revisión de la dirección.",
        ),
        (
            ("mejora continua", "plan de mejora"),
            "10.1",
            92,
            "Contenido relacionado con mejora continua.",
        ),
        (
            (
                "no conformidad",
                "accion correctiva",
                "acciones correctivas",
                "medidas correctivas",
            ),
            "10.2",
            95,
            "Contenido relacionado con no conformidades/acciones correctivas.",
        ),
        (
            ("control de documentos", "documentos y registros", "validez"),
            "11",
            93,
            "Contenido relacionado con validez/gestión documental.",
        ),
    ]

    for tokens, code, confidence, reason in keyword_rules:
        if any(token in text for token in tokens):
            add_hit(hits, code, confidence, reason)

    if any(
        token in text
        for token in (
            "requisitos legales",
            "requisitos normativos",
            "requisitos contractuales",
        )
    ):
        add_hit(
            hits,
            "4.1",
            92,
            "Requisitos legales/normativos como entrada del contexto.",
        )
        add_hit(
            hits,
            "4.2",
            90,
            "Requisitos legales/normativos vinculados con partes interesadas.",
        )

    return hits


class Command(BaseCommand):
    help = (
        "Vincula documentos reales con las secciones 1-11 del Manual SGSI. "
        "Por defecto solo previsualiza; use --apply para guardar."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Guarda asignaciones y sincroniza Document.sgsi_sections.",
        )
        parser.add_argument(
            "--min-confidence",
            type=int,
            default=70,
            help="Confianza mínima. Por defecto: 70.",
        )
        parser.add_argument(
            "--show-documents",
            action="store_true",
            help="Muestra el detalle de cada documento.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        apply_changes = options["apply"]
        min_conf = options["min_confidence"]
        show_documents = options["show_documents"]

        sections = {
            section.code: section
            for section in SGSISection.objects.filter(is_active=True)
        }

        expected = {
            "3", "3.1", "3.2", "3.3", "3.4",
            "4.1", "4.2", "4.3", "4.4",
            "5.1", "5.2", "5.3",
            "6.1", "6.2", "6.3",
            "7.1", "7.2", "7.3", "7.4", "7.5",
            "8.1", "8.2", "8.3",
            "9.1", "9.2", "9.3",
            "10.1", "10.2", "11",
        }

        missing = sorted(expected - set(sections))
        if missing:
            raise CommandError(
                "Faltan secciones SGSI requeridas: "
                + ", ".join(missing)
            )

        documents = (
            Document.objects
            .prefetch_related("versions__source_artifact")
            .order_by("code")
        )

        predicted_assignments = 0
        docs_with_hits = 0
        docs_without_hits = 0
        by_section = Counter()
        desired = defaultdict(dict)

        for document in documents:
            hits = infer_sections(document)
            hits = {
                code: data
                for code, data in hits.items()
                if data["confidence"] >= min_conf
            }

            if hits:
                docs_with_hits += 1
            else:
                docs_without_hits += 1

            for code, data in hits.items():
                desired[document.id][code] = data
                predicted_assignments += 1
                by_section[code] += 1

            if show_documents:
                labels = ", ".join(
                    f"{code}({data['confidence']}%)"
                    for code, data in sorted(hits.items())
                ) or "(sin asignación)"
                self.stdout.write(
                    f"{document.code} | {document.title} | {labels}"
                )

        if apply_changes:
            DocumentSectionAssignment.objects.filter(
                method=SectionAssignmentMethod.AUTO,
            ).update(is_active=False)

            for document in documents:
                active_sections = []

                for code, data in desired.get(document.id, {}).items():
                    section = sections[code]

                    DocumentSectionAssignment.objects.update_or_create(
                        document=document,
                        section=section,
                        defaults={
                            "method": SectionAssignmentMethod.AUTO,
                            "confidence": data["confidence"],
                            "rule_version": RULE_VERSION,
                            "reason": data["reason"],
                            "is_active": True,
                        },
                    )
                    active_sections.append(section)

                manual_sections = SGSISection.objects.filter(
                    document_assignments__document=document,
                    document_assignments__is_active=True,
                    document_assignments__method__in=(
                        SectionAssignmentMethod.MANUAL,
                        SectionAssignmentMethod.MANUAL_REFERENCE,
                    ),
                ).distinct()

                combined = list(active_sections) + list(manual_sections)
                document.sgsi_sections.set(combined)

        self.stdout.write("=== MAPEO MANUAL SGSI ===")
        self.stdout.write(
            f"Modo: {'APPLY' if apply_changes else 'PREVIEW'}"
        )
        self.stdout.write(
            f"Documentos analizados: {documents.count()}"
        )
        self.stdout.write(
            f"Documentos con asignación: {docs_with_hits}"
        )
        self.stdout.write(
            f"Documentos sin asignación automática: {docs_without_hits}"
        )
        self.stdout.write(
            f"Asignaciones previstas: {predicted_assignments}"
        )
        self.stdout.write(
            f"Regla: {RULE_VERSION}"
        )

        self.stdout.write("")
        self.stdout.write("=== ASIGNACIONES POR SECCIÓN ===")
        for code, total in sorted(
            by_section.items(),
            key=lambda pair: (
                sections[pair[0]].sort_order,
                pair[0],
            ),
        ):
            section = sections[code]
            self.stdout.write(
                f"{code:<5} | {total:>3} | {section.title}"
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
            active = DocumentSectionAssignment.objects.filter(
                is_active=True
            ).count()
            self.stdout.write("")
            self.stdout.write(
                f"Asignaciones activas persistidas: {active}"
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "Vinculación documental al Manual SGSI finalizada."
                )
            )
