from django.db.models import ProtectedError
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .models import (
    ProcessCategory,
    ProcessCategoryRelation,
    ProcessNode,
    ProcessReferenceDocument,
    ProcessReferenceVersion,
    ProcessRelation,
)


PROTECTED = (
    ProcessCategory,
    ProcessNode,
    ProcessRelation,
    ProcessCategoryRelation,
    ProcessReferenceDocument,
    ProcessReferenceVersion,
)


@receiver(pre_delete)
def block_process_physical_delete(sender, instance, using, **kwargs):
    if sender in PROTECTED:
        raise ProtectedError(
            "Los registros de procesos no se eliminan físicamente. "
            "Use desactivación para conservar trazabilidad.",
            [instance],
        )
