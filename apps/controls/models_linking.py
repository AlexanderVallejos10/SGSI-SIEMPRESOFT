from django.db import models

from apps.core.models import TraceableModel


class ControlDocumentMatchMethod(models.TextChoices):
    EXACT_REFERENCE = "exact_reference", "Referencia textual exacta"
    FUZZY_REFERENCE = "fuzzy_reference", "Referencia textual normalizada"
    MANUAL = "manual", "Asignación manual"


class ControlDocumentAssignment(TraceableModel):
    control = models.ForeignKey(
        "controls.Control",
        on_delete=models.PROTECT,
        related_name="document_assignments",
    )

    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.PROTECT,
        related_name="control_assignments",
    )

    support_reference = models.ForeignKey(
        "controls.ControlSupportReference",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="document_assignments",
    )

    method = models.CharField(
        max_length=24,
        choices=ControlDocumentMatchMethod.choices,
        default=ControlDocumentMatchMethod.EXACT_REFERENCE,
        db_index=True,
    )

    confidence = models.PositiveSmallIntegerField(
        default=0,
        help_text="Confianza de la vinculación entre 0 y 100.",
    )

    matched_fragment = models.TextField(
        blank=True,
        help_text="Fragmento de la fuente que sustentó la vinculación.",
    )

    matched_alias = models.CharField(
        max_length=255,
        blank=True,
        help_text="Título o nombre de archivo utilizado para el emparejamiento.",
    )

    reason = models.TextField(
        blank=True,
    )

    rule_version = models.CharField(
        max_length=32,
        default="2026.09-control-doc-v1",
        db_index=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("control", "document"),
                name="uniq_control_document_assignment",
            )
        ]
        ordering = (
            "control__code",
            "-confidence",
            "document__code",
        )
        verbose_name = "asignación control-documento"
        verbose_name_plural = "asignaciones control-documento"

    def __str__(self):
        return f"{self.control} → {self.document}"
