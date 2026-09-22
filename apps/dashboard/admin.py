from django.contrib import admin

from apps.core.admin import NoDeleteAdminMixin

from .models import (
    DashboardSnapshot,
    DashboardSourceRow,
    SGSIMetric,
    SecurityObjective,
    ObjectiveAlignment,
    StrategicFactor,
)


@admin.register(DashboardSnapshot)
class DashboardSnapshotAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "code",
        "year",
        "source_name",
        "source_artifact",
        "is_active",
        "created_at",
    )
    search_fields = (
        "code",
        "source_name",
        "source_sha256",
        "source_artifact__code",
        "source_artifact__original_name",
    )
    list_filter = (
        "year",
        "is_active",
    )
    autocomplete_fields = (
        "source_artifact",
    )


@admin.register(DashboardSourceRow)
class DashboardSourceRowAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "snapshot",
        "sheet_name",
        "row_number",
    )
    search_fields = (
        "snapshot__code",
        "sheet_name",
    )
    list_filter = (
        "snapshot",
        "sheet_name",
    )
    autocomplete_fields = (
        "snapshot",
    )


@admin.register(SGSIMetric)
class SGSIMetricAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "snapshot",
        "measurement_id",
        "description",
        "pdca_cycle",
        "responsible",
        "indicator",
        "current_value_raw",
        "compliance_raw",
    )
    search_fields = (
        "measurement_id",
        "description",
        "sgsi_process",
        "responsible",
        "indicator",
    )
    list_filter = (
        "snapshot",
        "pdca_cycle",
        "compliance_raw",
    )
    autocomplete_fields = (
        "snapshot",
    )


@admin.register(SecurityObjective)
class SecurityObjectiveAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "snapshot",
        "measurement_id",
        "description",
        "responsible",
        "calculation_period",
        "indicator",
        "current_value_raw",
        "compliance_raw",
    )
    search_fields = (
        "measurement_id",
        "description",
        "responsible",
        "indicator",
    )
    list_filter = (
        "snapshot",
        "compliance_raw",
    )
    autocomplete_fields = (
        "snapshot",
    )


@admin.register(ObjectiveAlignment)
class ObjectiveAlignmentAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "snapshot",
        "matrix_type",
        "source_row",
        "source_code",
        "source_group",
        "objective_code",
        "relation_type",
    )
    search_fields = (
        "source_code",
        "source_group",
        "source_description",
        "objective_code",
    )
    list_filter = (
        "snapshot",
        "matrix_type",
        "relation_type",
    )
    autocomplete_fields = (
        "snapshot",
    )


@admin.register(StrategicFactor)
class StrategicFactorAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "snapshot",
        "factor_type",
        "category",
        "classification",
        "source_row",
    )
    search_fields = (
        "category",
        "factor",
    )
    list_filter = (
        "snapshot",
        "factor_type",
        "category",
    )
    autocomplete_fields = (
        "snapshot",
    )
