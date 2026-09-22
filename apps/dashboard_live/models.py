from decimal import Decimal

from django.db import models
from django.db.models import Q

from apps.core.models import TraceableModel


class AlignmentValue(models.TextChoices):
    NONE = "", "Sin relación"
    PRIMARY = "P", "Primario"
    SECONDARY = "S", "Secundario"


class MatrixType(models.TextChoices):
    MEFI = "MEFI", "MEFI"
    MEFE = "MEFE", "MEFE"


class FactorGroup(models.TextChoices):
    STRENGTH = "strength", "Fortalezas"
    WEAKNESS = "weakness", "Debilidades"
    OPPORTUNITY = "opportunity", "Oportunidades"
    THREAT = "threat", "Amenazas"


class DashboardDataset(TraceableModel):
    code = models.CharField(max_length=50, unique=True, db_index=True)
    original_name = models.CharField(max_length=255)
    file = models.FileField(upload_to="dashboard_live/source/%Y/%m/")
    checksum_sha256 = models.CharField(max_length=64, unique=True, db_index=True)
    version_label = models.CharField(max_length=50, blank=True)
    is_current = models.BooleanField(default=False, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("-is_current", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("is_current",),
                condition=Q(is_current=True),
                name="uniq_dash_live_current",
            )
        ]

    def __str__(self):
        return f"{self.original_name} [{self.version_label or self.code}]"


class DashboardMetric(TraceableModel):
    dataset = models.ForeignKey(DashboardDataset, on_delete=models.PROTECT, related_name="sgsi_metrics")
    metric_id = models.PositiveSmallIntegerField()
    source_row = models.PositiveSmallIntegerField()
    description = models.TextField()
    pdca_cycle = models.CharField(max_length=10, blank=True)
    sgsi_process = models.TextField(blank=True)
    method = models.TextField(blank=True)
    objective = models.TextField(blank=True)
    responsible_text = models.CharField(max_length=220, blank=True)
    responsible_position = models.ForeignKey(
        "organization.Position",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="dashboard_sgsi_metrics",
    )
    period = models.CharField(max_length=120, blank=True)
    indicator = models.CharField(max_length=80, blank=True)
    current_value = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    current_text = models.CharField(max_length=80, blank=True)
    excel_scale = models.DecimalField(max_digits=10, decimal_places=6, default=Decimal("1"))
    source_compliance = models.CharField(max_length=20, blank=True)
    action_plan = models.TextField(blank=True)

    class Meta:
        ordering = ("metric_id",)
        constraints = [
            models.UniqueConstraint(
                fields=("dataset", "metric_id"),
                name="uniq_dash_live_sgsi_metric",
            )
        ]

    def __str__(self):
        return f"SGSI-{self.metric_id} {self.description[:70]}"


class OesiMetric(TraceableModel):
    dataset = models.ForeignKey(DashboardDataset, on_delete=models.PROTECT, related_name="oesi_metrics")
    metric_id = models.PositiveSmallIntegerField()
    source_row = models.PositiveSmallIntegerField()
    description = models.TextField()
    method = models.TextField(blank=True)
    responsible_text = models.CharField(max_length=220, blank=True)
    responsible_position = models.ForeignKey(
        "organization.Position",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="dashboard_oesi_metrics",
    )
    period = models.CharField(max_length=120, blank=True)
    indicator = models.CharField(max_length=80, blank=True)
    current_value = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    current_text = models.CharField(max_length=80, blank=True)
    excel_scale = models.DecimalField(max_digits=10, decimal_places=6, default=Decimal("1"))
    source_compliance = models.CharField(max_length=20, blank=True)
    record_label = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("metric_id",)
        constraints = [
            models.UniqueConstraint(
                fields=("dataset", "metric_id"),
                name="uniq_dash_live_oesi_metric",
            )
        ]

    def __str__(self):
        return f"OESI-{self.metric_id} {self.description[:70]}"


class StrategicObjective(TraceableModel):
    dataset = models.ForeignKey(DashboardDataset, on_delete=models.PROTECT, related_name="strategic_objectives")
    code = models.CharField(max_length=20)
    description = models.TextField()
    source_row = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ("source_row",)
        constraints = [
            models.UniqueConstraint(fields=("dataset", "code"), name="uniq_dash_live_oee")
        ]

    def __str__(self):
        return self.code


class SecurityObjective(TraceableModel):
    dataset = models.ForeignKey(DashboardDataset, on_delete=models.PROTECT, related_name="security_objectives")
    code = models.CharField(max_length=20)
    description = models.TextField()
    source_column = models.CharField(max_length=4)
    sort_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ("sort_order",)
        constraints = [
            models.UniqueConstraint(fields=("dataset", "code"), name="uniq_dash_live_osi")
        ]

    def __str__(self):
        return self.code


class OeeOsiAlignment(TraceableModel):
    dataset = models.ForeignKey(DashboardDataset, on_delete=models.PROTECT, related_name="oee_osi_alignments")
    strategic_objective = models.ForeignKey(StrategicObjective, on_delete=models.PROTECT, related_name="security_alignments")
    security_objective = models.ForeignKey(SecurityObjective, on_delete=models.PROTECT, related_name="strategic_alignments")
    relation = models.CharField(max_length=1, choices=AlignmentValue.choices, blank=True, default="")
    source_cell = models.CharField(max_length=12)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("dataset", "strategic_objective", "security_objective"),
                name="uniq_dash_live_oee_osi",
            )
        ]


class StakeholderRequirement(TraceableModel):
    dataset = models.ForeignKey(DashboardDataset, on_delete=models.PROTECT, related_name="stakeholder_requirements")
    source_row = models.PositiveSmallIntegerField()
    stakeholder = models.CharField(max_length=220, blank=True)
    requirement = models.TextField()

    class Meta:
        ordering = ("source_row",)
        constraints = [
            models.UniqueConstraint(fields=("dataset", "source_row"), name="uniq_dash_live_req_row")
        ]

    def __str__(self):
        return f"{self.stakeholder or 'Continuación'} - {self.requirement[:60]}"


class RequirementOsiAlignment(TraceableModel):
    dataset = models.ForeignKey(DashboardDataset, on_delete=models.PROTECT, related_name="requirement_osi_alignments")
    requirement = models.ForeignKey(StakeholderRequirement, on_delete=models.PROTECT, related_name="security_alignments")
    security_objective = models.ForeignKey(SecurityObjective, on_delete=models.PROTECT, related_name="requirement_alignments")
    relation = models.CharField(max_length=1, choices=AlignmentValue.choices, blank=True, default="")
    source_cell = models.CharField(max_length=12)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("dataset", "requirement", "security_objective"),
                name="uniq_dash_live_req_osi",
            )
        ]


class StrategicFactor(TraceableModel):
    dataset = models.ForeignKey(DashboardDataset, on_delete=models.PROTECT, related_name="strategic_factors")
    matrix_type = models.CharField(max_length=10, choices=MatrixType.choices, db_index=True)
    group = models.CharField(max_length=20, choices=FactorGroup.choices, db_index=True)
    source_row = models.PositiveSmallIntegerField()
    description = models.TextField()
    weight = models.DecimalField(max_digits=8, decimal_places=4)
    classification = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ("matrix_type", "source_row")
        constraints = [
            models.UniqueConstraint(
                fields=("dataset", "matrix_type", "source_row"),
                name="uniq_dash_live_factor",
            )
        ]

    @property
    def score(self):
        return self.weight * Decimal(self.classification)

    def __str__(self):
        return f"{self.matrix_type} {self.source_row}: {self.description[:60]}"


class DashboardCellTrace(TraceableModel):
    dataset = models.ForeignKey(DashboardDataset, on_delete=models.PROTECT, related_name="cell_traces")
    entity_type = models.CharField(max_length=40, db_index=True)
    entity_key = models.CharField(max_length=80, db_index=True)
    field_name = models.CharField(max_length=80)
    source_sheet = models.CharField(max_length=160)
    source_cell = models.CharField(max_length=20)
    source_formula = models.TextField(blank=True)
    source_value = models.TextField(blank=True)

    class Meta:
        ordering = ("source_sheet", "source_cell")


class DashboardChange(TraceableModel):
    dataset = models.ForeignKey(DashboardDataset, on_delete=models.PROTECT, related_name="changes")
    entity_type = models.CharField(max_length=40, db_index=True)
    entity_key = models.CharField(max_length=80, db_index=True)
    field_name = models.CharField(max_length=80)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    source_sheet = models.CharField(max_length=160, blank=True)
    source_cell = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ("-created_at",)
