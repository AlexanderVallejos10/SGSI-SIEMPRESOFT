from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Asset, AssetMovement, AssetStatus, MovementType


@transaction.atomic
def assign_asset(*, asset: Asset, user, actor, reason="") -> AssetMovement:
    asset = Asset.objects.select_for_update().get(pk=asset.pk)
    if asset.status != AssetStatus.AVAILABLE:
        raise ValidationError("El activo no se encuentra disponible para asignación.")
    movement = AssetMovement.objects.create(
        movement_type=MovementType.ASSIGNMENT,
        asset=asset,
        user=user,
        occurred_at=timezone.now(),
        reason=reason,
        created_by=actor,
        updated_by=actor,
    )
    asset.status = AssetStatus.ASSIGNED
    asset.custodian = user
    asset.updated_by = actor
    asset.save(update_fields=["status", "custodian", "updated_by", "updated_at"])
    return movement


@transaction.atomic
def return_asset(*, asset: Asset, actor, reason="") -> AssetMovement:
    asset = Asset.objects.select_for_update().get(pk=asset.pk)
    if asset.status != AssetStatus.ASSIGNED:
        raise ValidationError("El activo no tiene una asignación vigente.")
    previous_user = asset.custodian
    movement = AssetMovement.objects.create(
        movement_type=MovementType.RETURN,
        asset=asset,
        user=previous_user,
        occurred_at=timezone.now(),
        reason=reason,
        created_by=actor,
        updated_by=actor,
    )
    asset.status = AssetStatus.AVAILABLE
    asset.custodian = None
    asset.updated_by = actor
    asset.save(update_fields=["status", "custodian", "updated_by", "updated_at"])
    return movement
