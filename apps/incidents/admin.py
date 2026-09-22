from django.contrib import admin

from apps.core.admin import NoDeleteAdminMixin

from .models import (
    Incident,
    IncidentEvent,
    Vulnerability,
)


@admin.register(Incident)
class IncidentAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    pass


@admin.register(IncidentEvent)
class IncidentEventAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    pass


@admin.register(Vulnerability)
class VulnerabilityAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    pass