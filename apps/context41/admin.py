from django.contrib import admin

from apps.core.admin import NoDeleteAdminMixin

from .models import (
    ContextDocument,
    ContextDocumentVersion,
    LegalRequirement,
)


@admin.register(ContextDocument)
class ContextDocumentAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "title",
        "kind",
        "sort_order",
        "is_active",
    )
    search_fields = (
        "title",
        "description",
    )
    list_filter = (
        "kind",
        "is_active",
    )


@admin.register(ContextDocumentVersion)
class ContextDocumentVersionAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "document",
        "version_label",
        "is_current",
        "original_name",
        "created_at",
    )
    search_fields = (
        "document__title",
        "version_label",
        "original_name",
        "checksum_sha256",
    )
    list_filter = (
        "is_current",
        "document__kind",
    )
    autocomplete_fields = (
        "document",
        "source_artifact",
    )


@admin.register(LegalRequirement)
class LegalRequirementAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "number",
        "promulgated_by",
        "responsible",
        "status",
        "version",
    )
    search_fields = (
        "requirement",
        "promulgated_by",
        "responsible",
        "interested_parties",
    )
    list_filter = (
        "status",
        "promulgated_by",
    )
    autocomplete_fields = (
        "version",
    )
