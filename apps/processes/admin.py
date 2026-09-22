from django.contrib import admin

from .models import (
    ProcessCategory,
    ProcessCategoryRelation,
    ProcessNode,
    ProcessReferenceDocument,
    ProcessReferenceVersion,
    ProcessRelation,
)


class NoDeleteAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProcessCategory)
class ProcessCategoryAdmin(NoDeleteAdmin):
    list_display = (
        "code",
        "name",
        "kind",
        "sort_order",
        "is_active",
    )
    search_fields = ("code", "name")


@admin.register(ProcessNode)
class ProcessNodeAdmin(NoDeleteAdmin):
    list_display = (
        "code",
        "name",
        "category",
        "owner_position",
        "is_in_scope",
        "is_active",
    )
    list_filter = (
        "category",
        "is_in_scope",
        "is_active",
    )
    search_fields = (
        "code",
        "name",
        "description",
    )
    filter_horizontal = (
        "involved_areas",
        "involved_positions",
        "participants",
        "documents",
        "controls",
        "risks",
        "assets",
    )


@admin.register(ProcessRelation)
class ProcessRelationAdmin(NoDeleteAdmin):
    list_display = (
        "source",
        "target",
        "relation_type",
        "is_active",
    )


@admin.register(ProcessCategoryRelation)
class ProcessCategoryRelationAdmin(NoDeleteAdmin):
    list_display = (
        "source",
        "target",
        "relation_type",
        "is_active",
    )


@admin.register(ProcessReferenceDocument)
class ProcessReferenceDocumentAdmin(NoDeleteAdmin):
    list_display = (
        "title",
        "kind",
        "is_active",
    )


@admin.register(ProcessReferenceVersion)
class ProcessReferenceVersionAdmin(NoDeleteAdmin):
    list_display = (
        "document",
        "version_label",
        "is_current",
        "created_at",
    )
