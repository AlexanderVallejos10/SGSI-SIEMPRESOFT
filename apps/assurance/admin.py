from django.contrib import admin

from apps.core.admin import NoDeleteAdminMixin

from .models import (
    Audit,
    Finding,
    ImprovementAction,
)


@admin.register(Audit)
class AuditAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    pass


@admin.register(Finding)
class FindingAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    pass


@admin.register(ImprovementAction)
class ImprovementActionAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    pass