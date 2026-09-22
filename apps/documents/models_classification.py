from django.db import models

from apps.core.models import TraceableModel


class SourceLifecycleHint(models.TextChoices):
    CURRENT = "vigente", "Vigente"
    OBSOLETE = "no_vigente", "No vigente"
    DRAFT = "borrador", "Borrador"
    HISTORICAL = "historico", "Histórico"
    UNKNOWN = "sin_clasificar", "Sin clasificar"


class SourceDocumentFamily(models.TextChoices):
    POLICY = "politica", "Política"
    MANUAL = "manual", "Manual"
    PROCEDURE = "procedimiento", "Procedimiento"
    INSTRUCTION = "instructivo", "Instructivo"
    GUIDE = "guia", "Guía"
    STANDARD = "estandar", "Estándar"
    MATRIX = "matriz", "Matriz"
    DASHBOARD = "dashboard", "Dashboard"
    FORMAT = "formato", "Formato"
    TEMPLATE = "plantilla", "Plantilla"
    REGISTER = "registro", "Registro"
    MINUTES = "acta", "Acta"
    REPORT = "reporte", "Reporte"
    INFORM = "informe", "Informe"
    EVIDENCE = "evidencia", "Evidencia"
    SPREADSHEET = "hoja_calculo", "Hoja de cálculo"
    PDF_OTHER = "pdf_otro", "PDF - otro"
    TEXT_DOCUMENT = "documento_texto", "Documento de texto"
    PRESENTATION = "presentacion", "Presentación"
    IMAGE = "imagen", "Imagen"
    REPORT_TEMPLATE = "plantilla_reporte", "Plantilla de reporte"
    TECHNICAL_BINARY = "binario_tecnico", "Binario técnico"
    TECHNICAL_SCRIPT = "script_config", "Script / configuración"
    TECHNICAL_TEXT = "texto_tecnico", "Texto técnico"
    ARCHIVE = "archivo_comprimido", "Archivo comprimido"
    OTHER = "otro", "Otro"


class SourceSGSIRelevance(models.TextChoices):
    CORE = "nucleo_sgsi", "Núcleo SGSI"
    SUPPORTING = "soporte_sgsi", "Soporte / evidencia SGSI"
    OPERATIONAL = "operacional", "Operacional"
    TECHNICAL = "tecnico", "Técnico"
    UNKNOWN = "sin_clasificar", "Sin clasificar"


class SourceArtifactClassification(TraceableModel):
    artifact = models.OneToOneField(
        "documents.SourceArtifact",
        on_delete=models.PROTECT,
        related_name="classification",
    )
    lifecycle_hint = models.CharField(
        max_length=32,
        choices=SourceLifecycleHint.choices,
        default=SourceLifecycleHint.UNKNOWN,
        db_index=True,
    )
    family_hint = models.CharField(
        max_length=40,
        choices=SourceDocumentFamily.choices,
        default=SourceDocumentFamily.OTHER,
        db_index=True,
    )
    area_hint = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
    )
    sgsi_relevance = models.CharField(
        max_length=32,
        choices=SourceSGSIRelevance.choices,
        default=SourceSGSIRelevance.UNKNOWN,
        db_index=True,
    )
    is_document_candidate = models.BooleanField(
        default=False,
        db_index=True,
    )
    is_evidence_candidate = models.BooleanField(
        default=False,
        db_index=True,
    )
    is_dashboard_candidate = models.BooleanField(
        default=False,
        db_index=True,
    )
    confidence = models.PositiveSmallIntegerField(
        default=0,
        help_text="Confianza de clasificación automática entre 0 y 100.",
    )
    rule_version = models.CharField(
        max_length=32,
        default="2026.09-v1",
        db_index=True,
    )
    classification_reason = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["artifact__original_path", "artifact__original_name"]
        verbose_name = "clasificación de artefacto fuente"
        verbose_name_plural = "clasificaciones de artefactos fuente"

    def __str__(self):
        return (
            f"{self.artifact.code} | "
            f"{self.family_hint} | "
            f"{self.lifecycle_hint}"
        )
