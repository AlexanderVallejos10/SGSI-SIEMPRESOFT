from django.contrib import admin

from apps.core.admin import NoDeleteAdminMixin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "occurred_at",
        "user",
        "module",
        "action",
        "entity",
        "entity_id",
        "result",
    )

    list_filter = (
        "module",
        "action",
        "result",
    )

    search_fields = (
        "entity_id",
        "entity",
        "user__username",
        "user__business_code",
    )

    readonly_fields = [
        field.name
        for field in AuditLog._meta.fields
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        return False