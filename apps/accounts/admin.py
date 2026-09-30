from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.core.admin import NoDeleteAdminMixin

from .models import (
    AccessReview,
    CorporateSystem,
    SystemAccess,
    User,
)


@admin.register(User)
class SGSIUserAdmin(
    NoDeleteAdminMixin,
    UserAdmin,
):
    list_display = (
        "business_code",
        "username",
        "email",
        "area",
        "position",
        "status",
        "status_as_of",
        "is_active",
        "source_verified",
    )

    search_fields = (
        "business_code",
        "username",
        "first_name",
        "last_name",
        "email",
        "document_number",
    )

    list_filter = (
        "status",
        "source_verified",
        "area",
        "is_active",
        "is_staff",
    )

    fieldsets = UserAdmin.fieldsets + (
        (
            "SGSI",
            {
                "fields": (
                    "business_code",
                    "document_number",
                    "area",
                    "position",
                    "manager",
                    "employment_start",
                    "employment_end",
                    "status",
                    "status_as_of",
                )
            },
        ),
        (
            "Procedencia del dato",
            {
                "fields": (
                    "source_document",
                    "source_reference",
                    "source_verified",
                )
            },
        ),
    )


@admin.register(CorporateSystem)
class CorporateSystemAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "business_code",
        "name",
        "category",
        "status",
        "status_as_of",
        "authorization_authority",
        "source_verified",
    )

    search_fields = (
        "business_code",
        "name",
        "category",
        "authorization_authority",
        "technical_implementer",
        "source_document",
    )

    list_filter = (
        "status",
        "source_verified",
        "category",
    )


@admin.register(SystemAccess)
class SystemAccessAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "business_code",
        "user",
        "system",
        "role_profile",
        "status",
        "status_as_of",
        "is_privileged",
        "mfa_enabled",
        "source_verified",
    )

    search_fields = (
        "business_code",
        "user__business_code",
        "user__username",
        "user__first_name",
        "user__last_name",
        "system__business_code",
        "system__name",
        "role_profile",
        "approval_reference",
        "source_document",
    )

    list_filter = (
        "status",
        "is_privileged",
        "mfa_enabled",
        "source_verified",
        "system",
    )

    autocomplete_fields = (
        "user",
        "system",
        "approved_by",
    )


@admin.register(AccessReview)
class AccessReviewAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "business_code",
        "access",
        "reviewed_at",
        "decision",
        "reviewer",
        "next_review_at",
        "source_verified",
    )

    search_fields = (
        "business_code",
        "access__business_code",
        "access__user__business_code",
        "access__user__username",
        "access__system__name",
        "evidence_reference",
        "source_document",
    )

    list_filter = (
        "decision",
        "source_verified",
        "reviewed_at",
        "next_review_at",
    )

    autocomplete_fields = (
        "access",
        "reviewer",
    )

# ---------------------------------------------------------------- acceso al sistema (solo lectura: son registros)
from .models import LoginAttempt, Notification, PasswordChangeRequest, UserSession  # noqa: E402


class _ReadOnly(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(UserSession)
class UserSessionAdmin(_ReadOnly):
    list_display = ("user", "started_at", "last_seen_at", "ended_at", "ended_reason", "ip_address")
    list_filter = ("ended_reason",)
    search_fields = ("user__username", "user__first_name", "user__last_name", "ip_address")


@admin.register(LoginAttempt)
class LoginAttemptAdmin(_ReadOnly):
    list_display = ("username", "success", "ip_address", "created_at")
    list_filter = ("success",)
    search_fields = ("username", "ip_address")


@admin.register(PasswordChangeRequest)
class PasswordChangeRequestAdmin(_ReadOnly):
    list_display = ("user", "status", "created_at", "resolved_by", "resolved_at")
    list_filter = ("status",)


@admin.register(Notification)
class NotificationAdmin(_ReadOnly):
    list_display = ("recipient", "kind", "title", "created_at", "read_at")
    list_filter = ("kind",)
