from django.contrib import admin

from apps.core.admin import NoDeleteAdminMixin

from .models import (
    Control,
    ControlEvidence,
    ControlFramework,
)


@admin.register(ControlFramework)
class ControlFrameworkAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    pass


@admin.register(Control)
class ControlAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    pass


@admin.register(ControlEvidence)
class ControlEvidenceAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    pass

from .models_iso import (
    ControlSupportReference,
    ISOClause,
    ISODataQualityIssue,
    ISORequirement,
)


@admin.register(ISOClause)
class ISOClauseAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "framework",
        "code",
        "title",
        "parent",
        "level",
        "source_sheet",
        "source_row",
        "active",
    )
    search_fields = (
        "code",
        "title",
        "framework__code",
        "framework__name",
    )
    list_filter = (
        "framework",
        "level",
        "active",
    )
    raw_id_fields = (
        "framework",
    )

    autocomplete_fields = (
        "parent",
        "source_artifact",
    )


@admin.register(ISORequirement)
class ISORequirementAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "clause",
        "source_label",
        "source_row",
        "is_clause_heading",
        "source_artifact",
    )
    search_fields = (
        "clause__code",
        "description",
        "supporting_reference",
        "source_label",
    )
    list_filter = (
        "is_clause_heading",
        "clause__framework",
    )
    autocomplete_fields = (
        "clause",
        "source_artifact",
    )


@admin.register(ControlSupportReference)
class ControlSupportReferenceAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "control",
        "source_row",
        "raw_control_code",
        "source_artifact",
    )
    search_fields = (
        "control__code",
        "control__name",
        "supporting_reference",
        "raw_control_name",
    )
    raw_id_fields = (
        "control",
    )

    autocomplete_fields = (
        "source_artifact",
    )


@admin.register(ISODataQualityIssue)
class ISODataQualityIssueAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "code",
        "issue_type",
        "severity",
        "source_sheet",
        "source_row",
        "resolved",
    )
    search_fields = (
        "code",
        "description",
        "resolution_notes",
    )
    list_filter = (
        "issue_type",
        "severity",
        "resolved",
    )
    autocomplete_fields = (
        "source_artifact",
    )

from .models_linking import ControlDocumentAssignment


@admin.register(ControlDocumentAssignment)
class ControlDocumentAssignmentAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "control",
        "document",
        "method",
        "confidence",
        "rule_version",
        "is_active",
    )

    search_fields = (
        "control__code",
        "control__name",
        "document__code",
        "document__title",
        "matched_fragment",
        "matched_alias",
        "reason",
    )

    list_filter = (
        "method",
        "rule_version",
        "is_active",
    )

    raw_id_fields = (
        "control",
    )

    autocomplete_fields = (
        "document",
        "support_reference",
    )

