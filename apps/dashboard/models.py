from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TraceableModel


class DashboardSnapshot(TraceableModel):
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )

    year = models.PositiveSmallIntegerField(
        db_index=True,
    )

    source_artifact = models.ForeignKey(
        "documents.SourceArtifact",
        on_delete=models.PROTECT,
        related_name="dashboard_snapshots",
    )

    source_sha256 = models.CharField(
        max_length=64,
        db_index=True,
    )

    source_name = models.CharField(
        max_length=255,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    notes = models.TextField(
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("year", "source_sha256"),
                name="uniq_dashboard_year_sha",
            )
        ]
        ordering = ("-year", "-created_at")

    def __str__(self):
        return f"{self.code} - {self.year}"


class DashboardSourceRow(TraceableModel):
    snapshot = models.ForeignKey(
        DashboardSnapshot,
        on_delete=models.PROTECT,
        related_name="source_rows",
    )

    sheet_name = models.CharField(
        max_length=100,
        db_index=True,
    )

    row_number = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    payload = models.JSONField(
        default=dict,
        help_text=(
            "Celdas originales de la fila, incluyendo valor cacheado, "
            "fórmula y formato cuando existen."
        ),
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("snapshot", "sheet_name", "row_number"),
                name="uniq_dashboard_source_row",
            )
        ]
        ordering = ("snapshot", "sheet_name", "row_number")

    def __str__(self):
        return (
            f"{self.snapshot.code} | "
            f"{self.sheet_name} | fila {self.row_number}"
        )


class SGSIMetric(TraceableModel):
    snapshot = models.ForeignKey(
        DashboardSnapshot,
        on_delete=models.PROTECT,
        related_name="sgsi_metrics",
    )

    source_row = models.PositiveIntegerField()

    measurement_id = models.CharField(
        max_length=30,
        blank=True,
        db_index=True,
    )

    description = models.TextField()
    pdca_cycle = models.CharField(max_length=10, blank=True)
    sgsi_process = models.TextField(blank=True)
    method_resources = models.TextField(blank=True)
    measurement_objective = models.TextField(blank=True)
    responsible = models.CharField(max_length=180, blank=True)
    update_period = models.CharField(max_length=120, blank=True)
    indicator = models.CharField(max_length=120, blank=True)

    current_value_raw = models.CharField(
        max_length=120,
        blank=True,
    )

    current_value_numeric = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        null=True,
        blank=True,
    )

    current_number_format = models.CharField(
        max_length=120,
        blank=True,
    )

    calculation_formula = models.TextField(
        blank=True,
    )

    compliance_raw = models.CharField(
        max_length=30,
        blank=True,
        db_index=True,
    )

    compliance_formula = models.TextField(
        blank=True,
    )

    recommended_actions = models.TextField(
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("snapshot", "source_row"),
                name="uniq_sgsi_metric_source_row",
            )
        ]
        ordering = ("snapshot", "source_row")

    def __str__(self):
        return (
            f"{self.snapshot.year} | "
            f"{self.measurement_id} | {self.description[:80]}"
        )


class SecurityObjective(TraceableModel):
    snapshot = models.ForeignKey(
        DashboardSnapshot,
        on_delete=models.PROTECT,
        related_name="security_objectives",
    )

    source_row = models.PositiveIntegerField()

    measurement_id = models.CharField(
        max_length=30,
        db_index=True,
    )

    description = models.TextField()
    method_resources = models.TextField(blank=True)
    responsible = models.CharField(max_length=180, blank=True)
    calculation_period = models.CharField(max_length=120, blank=True)
    indicator = models.CharField(max_length=120, blank=True)

    current_value_raw = models.CharField(
        max_length=120,
        blank=True,
    )

    current_value_numeric = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        null=True,
        blank=True,
    )

    current_number_format = models.CharField(
        max_length=120,
        blank=True,
    )

    calculation_formula = models.TextField(
        blank=True,
    )

    compliance_raw = models.CharField(
        max_length=30,
        blank=True,
        db_index=True,
    )

    compliance_formula = models.TextField(
        blank=True,
    )

    source_compliance_override = models.CharField(
        max_length=30,
        blank=True,
        help_text=(
            "Valor adicional de la columna I del Dashboard OESI, "
            "preservado sin reinterpretación."
        ),
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("snapshot", "source_row"),
                name="uniq_security_objective_source_row",
            )
        ]
        ordering = ("snapshot", "source_row")

    def __str__(self):
        return (
            f"{self.snapshot.year} | "
            f"OESI {self.measurement_id} | {self.description[:80]}"
        )


class AlignmentRelationType(models.TextChoices):
    PRIMARY = "P", "Principal"
    SECONDARY = "S", "Secundaria"


class AlignmentMatrixType(models.TextChoices):
    OEE_OSI = "oee_osi", "OEE vs OSI"
    EPI_OSI = "epi_osi", "EPI vs OSI"


class ObjectiveAlignment(TraceableModel):
    snapshot = models.ForeignKey(
        DashboardSnapshot,
        on_delete=models.PROTECT,
        related_name="objective_alignments",
    )

    matrix_type = models.CharField(
        max_length=20,
        choices=AlignmentMatrixType.choices,
        db_index=True,
    )

    source_row = models.PositiveIntegerField()

    source_code = models.CharField(
        max_length=80,
        blank=True,
        db_index=True,
    )

    source_group = models.CharField(
        max_length=180,
        blank=True,
    )

    source_description = models.TextField(
        blank=True,
    )

    objective_code = models.CharField(
        max_length=30,
        db_index=True,
    )

    relation_type = models.CharField(
        max_length=2,
        choices=AlignmentRelationType.choices,
        db_index=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=(
                    "snapshot",
                    "matrix_type",
                    "source_row",
                    "objective_code",
                ),
                name="uniq_dashboard_objective_alignment",
            )
        ]
        ordering = (
            "snapshot",
            "matrix_type",
            "source_row",
            "objective_code",
        )

    def __str__(self):
        return (
            f"{self.get_matrix_type_display()} | "
            f"{self.source_code or self.source_group} → "
            f"{self.objective_code} ({self.relation_type})"
        )


class StrategicFactorType(models.TextChoices):
    INTERNAL = "internal", "Interno / MEFI"
    EXTERNAL = "external", "Externo / MEFE"


class StrategicFactor(TraceableModel):
    snapshot = models.ForeignKey(
        DashboardSnapshot,
        on_delete=models.PROTECT,
        related_name="strategic_factors",
    )

    factor_type = models.CharField(
        max_length=16,
        choices=StrategicFactorType.choices,
        db_index=True,
    )

    category = models.CharField(
        max_length=40,
        blank=True,
        db_index=True,
    )

    factor = models.TextField()

    classification = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
    )

    source_row = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("snapshot", "factor_type", "source_row"),
                name="uniq_dashboard_strategic_factor",
            )
        ]
        ordering = (
            "snapshot",
            "factor_type",
            "source_row",
        )

    def __str__(self):
        return (
            f"{self.get_factor_type_display()} | "
            f"{self.category} | {self.factor[:80]}"
        )
