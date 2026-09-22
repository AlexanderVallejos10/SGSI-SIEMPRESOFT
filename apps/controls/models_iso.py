from django.db import models

from apps.core.models import TraceableModel


class ISOIssueSeverity(models.TextChoices):
    INFO = "info", "Informativa"
    WARNING = "warning", "Advertencia"
    ERROR = "error", "Error"


class ISOIssueType(models.TextChoices):
    SOURCE_DISCREPANCY = "source_discrepancy", "Discrepancia en fuente"
    UNMATCHED_CONTROL = "unmatched_control", "Control no conciliado"
    CONTROL_COUNT = "control_count", "Cantidad de controles"
    CLAUSE_MAPPING = "clause_mapping", "Mapeo de cláusula"
    OTHER = "other", "Otra"


class ISOClause(TraceableModel):
    framework = models.ForeignKey(
        "controls.ControlFramework",
        on_delete=models.PROTECT,
        related_name="iso_clauses",
    )
    code = models.CharField(
        max_length=20,
        db_index=True,
    )
    title = models.CharField(
        max_length=255,
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    level = models.PositiveSmallIntegerField(
        default=1,
    )
    source_artifact = models.ForeignKey(
        "documents.SourceArtifact",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="iso_clauses",
    )
    source_sheet = models.CharField(
        max_length=100,
        blank=True,
    )
    source_row = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("framework", "code"),
                name="uniq_framework_iso_clause",
            )
        ]
        ordering = ("framework__code", "code")

    def __str__(self):
        return f"{self.framework.code}:{self.code} - {self.title}"


class ISORequirement(TraceableModel):
    clause = models.ForeignKey(
        ISOClause,
        on_delete=models.PROTECT,
        related_name="requirements",
    )
    source_label = models.CharField(
        max_length=30,
        blank=True,
    )
    description = models.TextField()
    supporting_reference = models.TextField(
        blank=True,
    )
    is_clause_heading = models.BooleanField(
        default=False,
        db_index=True,
    )
    source_artifact = models.ForeignKey(
        "documents.SourceArtifact",
        on_delete=models.PROTECT,
        related_name="iso_requirements",
    )
    source_sheet = models.CharField(
        max_length=100,
    )
    source_row = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("source_artifact", "source_sheet", "source_row"),
                name="uniq_iso_requirement_source_row",
            )
        ]
        ordering = ("clause__code", "source_row")

    def __str__(self):
        return (
            f"{self.clause.code} | {self.source_label} | "
            f"{self.description[:80]}"
        )


class ControlSupportReference(TraceableModel):
    control = models.ForeignKey(
        "controls.Control",
        on_delete=models.PROTECT,
        related_name="support_references",
    )
    supporting_reference = models.TextField(
        blank=True,
    )
    source_artifact = models.ForeignKey(
        "documents.SourceArtifact",
        on_delete=models.PROTECT,
        related_name="control_support_references",
    )
    source_sheet = models.CharField(
        max_length=100,
    )
    source_row = models.PositiveIntegerField()
    raw_control_code = models.CharField(
        max_length=30,
        blank=True,
    )
    raw_control_name = models.CharField(
        max_length=255,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("control", "source_artifact", "source_sheet", "source_row"),
                name="uniq_control_support_source_row",
            )
        ]
        ordering = ("control__code", "source_row")

    def __str__(self):
        return f"{self.control} | fila {self.source_row}"


class ISODataQualityIssue(TraceableModel):
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )
    issue_type = models.CharField(
        max_length=32,
        choices=ISOIssueType.choices,
        default=ISOIssueType.OTHER,
        db_index=True,
    )
    severity = models.CharField(
        max_length=16,
        choices=ISOIssueSeverity.choices,
        default=ISOIssueSeverity.WARNING,
        db_index=True,
    )
    description = models.TextField()
    source_artifact = models.ForeignKey(
        "documents.SourceArtifact",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="iso_quality_issues",
    )
    source_sheet = models.CharField(
        max_length=100,
        blank=True,
    )
    source_row = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    resolved = models.BooleanField(
        default=False,
        db_index=True,
    )
    resolution_notes = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ("resolved", "severity", "code")

    def __str__(self):
        return f"{self.code} - {self.get_issue_type_display()}"
