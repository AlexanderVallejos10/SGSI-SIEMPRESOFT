from django.contrib import admin

from apps.core.admin import NoDeleteAdminMixin

from .models import (
    OrganizationalArea,
    Position,
    PositionAssignment,
)


@admin.register(OrganizationalArea)
class OrganizationalAreaAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "code",
        "name",
        "parent",
        "sort_order",
        "is_active",
    )
    search_fields = (
        "code",
        "name",
        "description",
    )
    list_filter = (
        "is_active",
    )
    autocomplete_fields = (
        "parent",
    )


@admin.register(Position)
class PositionAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "code",
        "title",
        "area",
        "parent",
        "relation_type",
        "sort_order",
        "is_active",
    )
    search_fields = (
        "code",
        "title",
        "description",
    )
    list_filter = (
        "relation_type",
        "is_critical",
        "is_active",
        "area",
    )
    autocomplete_fields = (
        "area",
        "parent",
    )


@admin.register(PositionAssignment)
class PositionAssignmentAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "position",
        "user",
        "start_date",
        "end_date",
        "is_primary",
    )
    search_fields = (
        "position__code",
        "position__title",
        "user__username",
        "user__first_name",
        "user__last_name",
    )
    list_filter = (
        "is_primary",
        "start_date",
        "end_date",
    )
    autocomplete_fields = (
        "position",
        "user",
    )
