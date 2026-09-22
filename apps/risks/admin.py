from django.contrib import admin

from apps.core.admin import NoDeleteAdminMixin

from .models import (
    Risk,
    RiskAssessment,
    RiskTreatment,
)


@admin.register(Risk)
class RiskAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    pass


@admin.register(RiskAssessment)
class RiskAssessmentAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    pass


@admin.register(RiskTreatment)
class RiskTreatmentAdmin(
    NoDeleteAdminMixin,
    admin.ModelAdmin,
):
    pass