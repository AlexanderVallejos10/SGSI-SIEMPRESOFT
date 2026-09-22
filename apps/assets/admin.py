from django.contrib import admin

from apps.core.admin import NoDeleteAdminMixin

from .models import (
    Asset,
    AssetMovement,
    Maintenance,
)


@admin.register(Asset)
class AssetAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    pass


@admin.register(AssetMovement)
class AssetMovementAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    pass


@admin.register(Maintenance)
class MaintenanceAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    pass