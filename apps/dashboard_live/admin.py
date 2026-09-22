from django.contrib import admin

from .models import (
    DashboardCellTrace,
    DashboardChange,
    DashboardDataset,
    DashboardMetric,
    OeeOsiAlignment,
    OesiMetric,
    RequirementOsiAlignment,
    SecurityObjective,
    StakeholderRequirement,
    StrategicFactor,
    StrategicObjective,
)


class NoDeleteAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(DashboardDataset, NoDeleteAdmin)
admin.site.register(DashboardMetric, NoDeleteAdmin)
admin.site.register(OesiMetric, NoDeleteAdmin)
admin.site.register(StrategicObjective, NoDeleteAdmin)
admin.site.register(SecurityObjective, NoDeleteAdmin)
admin.site.register(OeeOsiAlignment, NoDeleteAdmin)
admin.site.register(StakeholderRequirement, NoDeleteAdmin)
admin.site.register(RequirementOsiAlignment, NoDeleteAdmin)
admin.site.register(StrategicFactor, NoDeleteAdmin)
admin.site.register(DashboardCellTrace, NoDeleteAdmin)
admin.site.register(DashboardChange, NoDeleteAdmin)
