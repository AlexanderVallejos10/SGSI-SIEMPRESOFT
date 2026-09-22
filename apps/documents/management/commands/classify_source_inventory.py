import re
import unicodedata
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.documents.models import SourceArtifact
from apps.documents.models_classification import (
    SourceArtifactClassification,
    SourceDocumentFamily,
    SourceLifecycleHint,
    SourceSGSIRelevance,
)


RULE_VERSION = "2026.09-v2"

TECHNICAL_EXTENSIONS = {
    "dll", "exe", "mrt", "sql", "ps1", "config", "json",
    "xml", "ini", "vpd", "bpm", "txt",
}

SGSI_ROOT_TOKENS = (
    "02 - area de seguridad de la informacion",
    "09 - paquete de documentos sobre iso 27001",
)

EVIDENCE_ROOT_TOKENS = (
    "evidencias de auditoria de controles ose",
)

OPERATIONAL_ROOT_TOKENS = (
    "area de administracion",
    "area de soporte al cliente",
    "area de produccion",
    "area de desarrollo",
    "area de consultoria",
    "proyectos",
)

CORE_TOKENS = (
    "sgsi",
    "seguridad de la informacion",
    "iso 27001",
    "iso27001",
    "politica de seguridad",
    "manual del sgsi",
    "alcance del sgsi",
    "riesgo",
    "auditoria",
    "control",
    "incidente",
    "vulnerabilidad",
    "continuidad",
    "parte interesada",
    "requisito legal",
)

SUPPORT_TOKENS = (
    "evidencia",
    "anexo",
    "registro",
    "acta",
    "verificacion",
    "dashboard sgsi",
)


def normalize(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(
        ch for ch in value if not unicodedata.combining(ch)
    )
    return value.casefold()


def clean_root(path):
    parts = [
        p.strip()
        for p in (path or "").replace("\\", "/").split("/")
        if p.strip()
    ]
    if not parts:
        return ""
    return re.sub(r"^_+", "", parts[0]).strip()[:255]


def lifecycle(path):
    text = normalize(path)

    if any(
        token in text
        for token in (
            "no vigente",
            "no vigentes",
            "obsoleto",
            "obsoletos",
            "deprecated",
        )
    ):
        return SourceLifecycleHint.OBSOLETE, 98, "Ruta indica documento no vigente."

    if any(token in text for token in ("borrador", "draft")):
        return SourceLifecycleHint.DRAFT, 96, "Ruta indica borrador."

    if any(
        token in text
        for token in (
            "documentos vigentes",
            "/vigentes/",
            " vigente",
        )
    ):
        return SourceLifecycleHint.CURRENT, 96, "Ruta indica documento vigente."

    if any(
        token in text
        for token in (
            "historico",
            "historica",
            "historial",
            "archivo historico",
        )
    ):
        return SourceLifecycleHint.HISTORICAL, 90, "Ruta indica contenido histórico."

    return SourceLifecycleHint.UNKNOWN, 35, "Sin señal concluyente de ciclo de vida."


def technical_family(ext):
    if ext == "mrt":
        return (
            SourceDocumentFamily.REPORT_TEMPLATE,
            99,
            "Extensión MRT: plantilla técnica de reporte.",
        )

    if ext in {"dll", "exe"}:
        return (
            SourceDocumentFamily.TECHNICAL_BINARY,
            99,
            f"Extensión técnica binaria: .{ext}.",
        )

    if ext in {"sql", "ps1", "config", "json", "xml", "ini", "vpd", "bpm"}:
        return (
            SourceDocumentFamily.TECHNICAL_SCRIPT,
            95,
            f"Extensión técnica/configuración: .{ext}.",
        )

    if ext == "txt":
        return (
            SourceDocumentFamily.TECHNICAL_TEXT,
            90,
            "TXT tratado como texto técnico en clasificación automática.",
        )

    return None


def family(name, path, extension):
    text = normalize(f"{name} {path}")
    ext = normalize(extension).lstrip(".")

    # V2: la extensión técnica tiene prioridad sobre palabras como
    # "formato", "registro" o "reporte" en el nombre.
    technical = technical_family(ext)
    if technical:
        return technical

    keyword_rules = (
        (SourceDocumentFamily.DASHBOARD, ("dashboard", "tablero")),
        (SourceDocumentFamily.POLICY, ("politica",)),
        (SourceDocumentFamily.MANUAL, ("manual",)),
        (SourceDocumentFamily.PROCEDURE, ("procedimiento",)),
        (SourceDocumentFamily.INSTRUCTION, ("instructivo",)),
        (SourceDocumentFamily.GUIDE, ("guia",)),
        (SourceDocumentFamily.STANDARD, ("estandar",)),
        (SourceDocumentFamily.MATRIX, ("matriz",)),
        (SourceDocumentFamily.FORMAT, ("formato", "formulario")),
        (SourceDocumentFamily.TEMPLATE, ("plantilla", "template")),
        (SourceDocumentFamily.REGISTER, ("registro",)),
        (SourceDocumentFamily.MINUTES, ("acta",)),
        (SourceDocumentFamily.INFORM, ("informe",)),
        (SourceDocumentFamily.REPORT, ("reporte",)),
        (SourceDocumentFamily.EVIDENCE, ("evidencia",)),
    )

    for label, tokens in keyword_rules:
        if any(token in text for token in tokens):
            return label, 88, f"Coincidencia nominal: {label}."

    if ext in {"xlsx", "xls", "xlsm", "csv", "ods"}:
        return (
            SourceDocumentFamily.SPREADSHEET,
            85,
            f"Extensión de hoja de cálculo: .{ext}.",
        )

    if ext == "pdf":
        return (
            SourceDocumentFamily.PDF_OTHER,
            70,
            "PDF sin término documental concluyente.",
        )

    if ext in {"doc", "docx", "odt"}:
        return (
            SourceDocumentFamily.TEXT_DOCUMENT,
            70,
            f"Documento de texto: .{ext}.",
        )

    if ext in {"ppt", "pptx", "odp"}:
        return (
            SourceDocumentFamily.PRESENTATION,
            85,
            f"Presentación: .{ext}.",
        )

    if ext in {
        "png", "jpg", "jpeg", "gif", "bmp",
        "tif", "tiff", "webp", "svg", "ico",
    }:
        return (
            SourceDocumentFamily.IMAGE,
            85,
            f"Archivo de imagen: .{ext}.",
        )

    if ext in {"zip", "rar", "7z", "tar", "gz", "backup"}:
        return (
            SourceDocumentFamily.ARCHIVE,
            85,
            f"Archivo comprimido/respaldo: .{ext}.",
        )

    return SourceDocumentFamily.OTHER, 45, "Sin regla documental específica."


def relevance(name, path, fam):
    text = normalize(f"{name} {path}")

    technical_families = {
        SourceDocumentFamily.REPORT_TEMPLATE,
        SourceDocumentFamily.TECHNICAL_BINARY,
        SourceDocumentFamily.TECHNICAL_SCRIPT,
        SourceDocumentFamily.TECHNICAL_TEXT,
    }

    if fam in technical_families:
        return SourceSGSIRelevance.TECHNICAL, 98, "Familia técnica."

    # Señales explícitas del núcleo SGSI tienen prioridad.
    if any(token in text for token in CORE_TOKENS):
        return (
            SourceSGSIRelevance.CORE,
            90,
            "Nombre/ruta contiene términos explícitos del núcleo SGSI.",
        )

    # El área Seguridad / paquete ISO sí puede contener documentos
    # núcleo o soportes.
    if any(token in text for token in SGSI_ROOT_TOKENS):
        if any(token in text for token in SUPPORT_TOKENS):
            return (
                SourceSGSIRelevance.SUPPORTING,
                92,
                "Ubicado en Seguridad/ISO y con señal de soporte/evidencia.",
            )
        return (
            SourceSGSIRelevance.CORE,
            92,
            "Ubicado en Seguridad de la Información/ISO 27001.",
        )

    # La carpeta de evidencias de auditoría se conserva como soporte SGSI.
    if any(token in text for token in EVIDENCE_ROOT_TOKENS):
        return (
            SourceSGSIRelevance.SUPPORTING,
            95,
            "Ubicado en evidencias de auditoría de controles OSE.",
        )

    # V2: si pertenece a un área operacional, palabras genéricas como
    # formato/registro/acta NO lo convierten en soporte SGSI.
    if any(token in text for token in OPERATIONAL_ROOT_TOKENS):
        return (
            SourceSGSIRelevance.OPERATIONAL,
            88,
            "Contenido perteneciente a un área operacional.",
        )

    # Solo fuera de áreas operacionales usamos señales genéricas de soporte.
    if any(token in text for token in SUPPORT_TOKENS):
        return (
            SourceSGSIRelevance.SUPPORTING,
            72,
            "Señal genérica de soporte/evidencia documental.",
        )

    return (
        SourceSGSIRelevance.UNKNOWN,
        45,
        "Sin señal concluyente de relevancia SGSI.",
    )


def candidate_flags(fam, rel, name, path):
    normalized = normalize(f"{name} {path}")

    dashboard = (
        fam == SourceDocumentFamily.DASHBOARD
        or "dashboard sgsi" in normalized
        or "verificacionnorma" in normalized
        or "verificacion norma" in normalized
    )

    evidence_families = {
        SourceDocumentFamily.EVIDENCE,
        SourceDocumentFamily.REGISTER,
        SourceDocumentFamily.MINUTES,
    }

    controlled_document_families = {
        SourceDocumentFamily.POLICY,
        SourceDocumentFamily.MANUAL,
        SourceDocumentFamily.PROCEDURE,
        SourceDocumentFamily.INSTRUCTION,
        SourceDocumentFamily.GUIDE,
        SourceDocumentFamily.STANDARD,
        SourceDocumentFamily.MATRIX,
        SourceDocumentFamily.DASHBOARD,
        SourceDocumentFamily.FORMAT,
        SourceDocumentFamily.TEMPLATE,
    }

    is_evidence = fam in evidence_families
    is_document = fam in controlled_document_families

    if fam in {
        SourceDocumentFamily.REPORT,
        SourceDocumentFamily.INFORM,
        SourceDocumentFamily.SPREADSHEET,
    }:
        if rel == SourceSGSIRelevance.SUPPORTING:
            is_evidence = True
        else:
            is_document = True

    if dashboard:
        is_document = True

    return is_document, is_evidence, dashboard


class Command(BaseCommand):
    help = (
        "Clasifica artefactos canónicos por reglas trazables V2. "
        "Por defecto solo previsualiza; use --apply para guardar."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Guarda las clasificaciones en PostgreSQL.",
        )
        parser.add_argument(
            "--include-duplicates",
            action="store_true",
            help="Incluye también ocurrencias marcadas como duplicadas.",
        )
        parser.add_argument(
            "--sample",
            type=int,
            default=25,
            help="Cantidad de ejemplos a mostrar.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        apply_changes = options["apply"]
        include_duplicates = options["include_duplicates"]
        sample_size = options["sample"]

        qs = SourceArtifact.objects.select_related("source_package")
        if not include_duplicates:
            qs = qs.filter(duplicate_of__isnull=True)

        total = qs.count()
        families = Counter()
        lifecycles = Counter()
        relevance_counts = Counter()
        doc_candidates = 0
        evidence_candidates = 0
        dashboard_candidates = 0
        samples = []

        self.stdout.write(f"Artefactos a clasificar: {total}")
        self.stdout.write(f"Modo: {'APPLY' if apply_changes else 'PREVIEW'}")
        self.stdout.write(f"Regla: {RULE_VERSION}")
        self.stdout.write("")

        for artifact in qs.iterator(chunk_size=500):
            life, life_conf, life_reason = lifecycle(artifact.original_path)
            fam, fam_conf, fam_reason = family(
                artifact.original_name,
                artifact.original_path,
                artifact.extension,
            )
            rel, rel_conf, rel_reason = relevance(
                artifact.original_name,
                artifact.original_path,
                fam,
            )
            is_doc, is_evidence, is_dashboard = candidate_flags(
                fam,
                rel,
                artifact.original_name,
                artifact.original_path,
            )

            confidence = round(
                (life_conf * 0.25)
                + (fam_conf * 0.45)
                + (rel_conf * 0.30)
            )

            reason = f"{life_reason} {fam_reason} {rel_reason}"

            families[fam] += 1
            lifecycles[life] += 1
            relevance_counts[rel] += 1
            doc_candidates += int(is_doc)
            evidence_candidates += int(is_evidence)
            dashboard_candidates += int(is_dashboard)

            if len(samples) < sample_size:
                samples.append(
                    (
                        artifact.code,
                        fam,
                        life,
                        rel,
                        confidence,
                        artifact.original_path,
                    )
                )

            if apply_changes:
                SourceArtifactClassification.objects.update_or_create(
                    artifact=artifact,
                    defaults={
                        "lifecycle_hint": life,
                        "family_hint": fam,
                        "area_hint": clean_root(artifact.original_path),
                        "sgsi_relevance": rel,
                        "is_document_candidate": is_doc,
                        "is_evidence_candidate": is_evidence,
                        "is_dashboard_candidate": is_dashboard,
                        "confidence": confidence,
                        "rule_version": RULE_VERSION,
                        "classification_reason": reason,
                    },
                )

        self.stdout.write("=== CICLO DE VIDA ===")
        for key, value in lifecycles.most_common():
            self.stdout.write(f"{key}: {value}")

        self.stdout.write("")
        self.stdout.write("=== FAMILIAS ===")
        for key, value in families.most_common():
            self.stdout.write(f"{key}: {value}")

        self.stdout.write("")
        self.stdout.write("=== RELEVANCIA SGSI ===")
        for key, value in relevance_counts.most_common():
            self.stdout.write(f"{key}: {value}")

        self.stdout.write("")
        self.stdout.write(f"Candidatos Document: {doc_candidates}")
        self.stdout.write(f"Candidatos Evidence: {evidence_candidates}")
        self.stdout.write(
            f"Candidatos Dashboard/Verificación: {dashboard_candidates}"
        )

        self.stdout.write("")
        self.stdout.write("=== MUESTRA ===")
        for code, fam, life, rel, conf, path in samples:
            self.stdout.write(
                f"{code} | {fam} | {life} | {rel} | {conf}% | {path}"
            )

        if not apply_changes:
            transaction.set_rollback(True)
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "PREVIEW: no se guardó ninguna clasificación."
                )
            )
        else:
            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    "Clasificaciones V2 guardadas correctamente."
                )
            )
