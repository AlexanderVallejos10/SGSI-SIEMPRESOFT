from django.db import models
from django.db.models import Q

from apps.core.models import TraceableModel


class ContextDocumentKind(models.TextChoices):
    MISSION_FODA = "mission_foda", "Misión, Visión y FODA"
    ORGANIZATION = "organization", "Organigrama"
    LEGAL = "legal", "Requisitos legales"


class ContextDocument(TraceableModel):
    slug = models.SlugField(
        max_length=60,
        unique=True,
        db_index=True,
    )
    title = models.CharField(
        max_length=220,
    )
    kind = models.CharField(
        max_length=30,
        choices=ContextDocumentKind.choices,
        unique=True,
        db_index=True,
    )
    description = models.TextField(
        blank=True,
    )
    source_location = models.TextField(
        blank=True,
    )
    sort_order = models.PositiveSmallIntegerField(
        default=100,
        db_index=True,
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = ("sort_order", "title")

    def __str__(self):
        return self.title


class ContextDocumentVersion(TraceableModel):
    document = models.ForeignKey(
        ContextDocument,
        on_delete=models.PROTECT,
        related_name="versions",
    )
    version_label = models.CharField(
        max_length=40,
    )
    source_artifact = models.ForeignKey(
        "documents.SourceArtifact",
        on_delete=models.PROTECT,
        related_name="context41_versions",
    )
    original_name = models.CharField(
        max_length=255,
    )
    checksum_sha256 = models.CharField(
        max_length=64,
        db_index=True,
    )
    is_current = models.BooleanField(
        default=False,
        db_index=True,
    )
    notes = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ("-is_current", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("document", "checksum_sha256"),
                name="uniq_ctx41_doc_checksum",
            ),
            models.UniqueConstraint(
                fields=("document",),
                condition=Q(is_current=True),
                name="uniq_ctx41_current_ver",
            ),
        ]

    def __str__(self):
        return (
            f"{self.document.title} "
            f"{self.version_label}"
        )


class LegalRequirement(TraceableModel):
    version = models.ForeignKey(
        ContextDocumentVersion,
        on_delete=models.PROTECT,
        related_name="legal_requirements",
    )
    source_row = models.PositiveIntegerField()
    number = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
    )
    requirement = models.TextField()
    promulgated_by = models.CharField(
        max_length=220,
        blank=True,
        db_index=True,
    )
    location = models.TextField(
        blank=True,
    )
    responsible = models.CharField(
        max_length=220,
        blank=True,
        db_index=True,
    )
    interested_parties = models.TextField(
        blank=True,
    )
    status = models.CharField(
        max_length=60,
        blank=True,
        db_index=True,
    )

    class Meta:
        ordering = ("number", "source_row")
        constraints = [
            models.UniqueConstraint(
                fields=("version", "source_row"),
                name="uniq_ctx41_legal_row",
            )
        ]
        indexes = [
            models.Index(
                fields=("version", "status"),
                name="ctx41_legal_status_idx",
            )
        ]

    def __str__(self):
        return (
            f"{self.number or self.source_row} - "
            f"{self.requirement[:90]}"
        )
