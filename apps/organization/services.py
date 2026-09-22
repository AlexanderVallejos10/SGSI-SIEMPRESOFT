from django.db import transaction
from django.utils import timezone

from .models import PositionAssignment


@transaction.atomic
def assign_user_to_position(
    *,
    assignment,
    actor=None,
):
    user = assignment.user
    position = assignment.position

    if assignment.is_primary:
        PositionAssignment.objects.filter(
            user=user,
            end_date__isnull=True,
            is_primary=True,
        ).exclude(pk=assignment.pk).update(
            end_date=assignment.start_date,
            updated_by=actor,
        )

    assignment.created_by = (
        actor
        if assignment.pk is None
        else assignment.created_by
    )
    assignment.updated_by = actor
    assignment.full_clean()
    assignment.save()

    update_fields = []

    if hasattr(user, "position"):
        user.position = position.title
        update_fields.append("position")

    if hasattr(user, "area") and position.area_id:
        user.area = position.area.name
        update_fields.append("area")

    if update_fields:
        update_fields.append("updated_at")
        user.save(update_fields=update_fields)

    return assignment


@transaction.atomic
def close_assignment(
    *,
    assignment,
    actor=None,
):
    assignment.end_date = timezone.localdate()
    assignment.updated_by = actor
    assignment.save(
        update_fields=(
            "end_date",
            "updated_by",
            "updated_at",
        )
    )

    return assignment
