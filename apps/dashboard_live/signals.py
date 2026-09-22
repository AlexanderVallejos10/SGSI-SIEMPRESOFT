from django.db.models import ProtectedError
from django.db.models.signals import pre_delete
from django.dispatch import receiver

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

PROTECTED = (
    DashboardDataset,
    DashboardMetric,
    OesiMetric,
    StrategicObjective,
    SecurityObjective,
    OeeOsiAlignment,
    StakeholderRequirement,
    RequirementOsiAlignment,
    StrategicFactor,
    DashboardCellTrace,
    DashboardChange,
)


@receiver(pre_delete)
def block_dashboard_live_delete(sender, instance, using, **kwargs):
    if sender in PROTECTED:
        raise ProtectedError(
            "Los registros del Dashboard SGSI no se eliminan físicamente; se conserva trazabilidad.",
            [instance],
        )
