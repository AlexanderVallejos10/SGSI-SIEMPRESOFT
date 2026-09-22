from django.db import models
from django.db.models import Q

from apps.core.models import TraceableModel


class RepresentationType(models.TextChoices):
    PUBLISHED_PDF = "published_pdf", "PDF publicado"
    EDITABLE_SOURCE = "editable_source", "Fuente editable"
    SPREADSHEET = "spreadsheet", "Hoja de cálculo"
    PRESENTATION = "presentation", "Presentación"
    OTHER = "other", "Otra representación"


class ImportIssueType(models.TextChoices):
    VERSION_CONFLICT = "version_conflict", "Conflicto de versión"
    AMBIGUOUS_VERSION = "ambiguous_version", "Versión ambigua"
    AMBIGUOUS_GROUP = "ambiguous_group", "Agrupación ambigua"
    SOURCE_MISSING = "source_missing", "Fuente faltante"
    OTHER = "other", "Otra incidencia"


class ImportIssueStatus(models.TextChoices):
    OPEN = "open", "Abierta"
    RESOLVED = "resolved", "Resuelta"
    IGNORED = "ignored", "Ignorada justificadamente"


class DocumentVersionRepresentation(TraceableModel):
    document_version = models.ForeignKey(
        "documents.DocumentVersion",
        on_delete=models.PROTECT,
        related_name="representations",
    )

    source_artifact = models.OneToOneField(
        "documents.SourceArtifact",
        on_delete=models.PROTECT,
        related_name="version_representation",
        help_text=(
            "Artefacto fuente verificado que contiene esta "
            "representación física de la versión."
        ),
    )

    representation_type = models.CharField(
        max_length=32,
        choices=RepresentationType.choices,
        default=RepresentationType.OTHER,
        db_index=True,
    )

    is_primary = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "Indica la representación principal de la versión "
            "(por ejemplo, PDF publicado)."
        ),
    )

    notes = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = (
            "document_version__document__code",
            "document_version__version",
            "-is_primary",
            "representation_type",
        )

        constraints = [
            models.UniqueConstraint(
                fields=("document_version",),
                condition=Q(is_primary=True),
                name="uniq_primary_representation_per_version",
            )
        ]

        verbose_name = "representación de versión documental"
        verbose_name_plural = "representaciones de versiones documentales"

    def __str__(self):
        return (
            f"{self.document_version} | "
            f"{self.get_representation_type_display()}"
        )


class DocumentImportIssue(TraceableModel):
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )

    issue_type = models.CharField(
        max_length=32,
        choices=ImportIssueType.choices,
        default=ImportIssueType.OTHER,
        db_index=True,
    )

    status = models.CharField(
        max_length=20,
        choices=ImportIssueStatus.choices,
        default=ImportIssueStatus.OPEN,
        db_index=True,
    )

    group_key = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text=(
            "Huella de la identidad documental detectada durante "
            "la promoción/importación."
        ),
    )

    document = models.ForeignKey(
        "documents.Document",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="import_issues",
    )

    version_label = models.CharField(
        max_length=30,
        blank=True,
    )

    title = models.CharField(
        max_length=255,
    )

    description = models.TextField()

    resolution_notes = models.TextField(
        blank=True,
    )

    source_artifacts = models.ManyToManyField(
        "documents.SourceArtifact",
        blank=True,
        related_name="document_import_issues",
    )

    class Meta:
        ordering = (
            "status",
            "issue_type",
            "code",
        )

        verbose_name = "incidencia de importación documental"
        verbose_name_plural = "incidencias de importación documental"

    def __str__(self):
        return f"{self.code} - {self.title}"
