from django.db import models

from apps.core.models import TraceableModel


class SectionAssignmentMethod(models.TextChoices):
    AUTO = "auto", "Regla automática"
    MANUAL = "manual", "Asignación manual"
    MANUAL_REFERENCE = "manual_reference", "Referencia explícita del Manual SGSI"


class DocumentSectionAssignment(TraceableModel):
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.PROTECT,
        related_name="section_assignments",
    )

    section = models.ForeignKey(
        "documents.SGSISection",
        on_delete=models.PROTECT,
        related_name="document_assignments",
    )

    method = models.CharField(
        max_length=24,
        choices=SectionAssignmentMethod.choices,
        default=SectionAssignmentMethod.AUTO,
        db_index=True,
    )

    confidence = models.PositiveSmallIntegerField(
        default=0,
        help_text="Confianza de la asignación entre 0 y 100.",
    )

    rule_version = models.CharField(
        max_length=32,
        default="2026.09-section-v1",
        db_index=True,
    )

    reason = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("document", "section"),
                name="uniq_document_sgsi_section_assignment",
            )
        ]

        ordering = (
            "section__sort_order",
            "section__code",
            "document__code",
        )

        verbose_name = "asignación documental a sección SGSI"
        verbose_name_plural = "asignaciones documentales a secciones SGSI"

    def __str__(self):
        return (
            f"{self.document.code} → "
            f"{self.section.code} {self.section.title}"
        )
