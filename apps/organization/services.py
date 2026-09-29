from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Position, PositionAssignment


@transaction.atomic
def save_area(*, form, actor):
    """Save an area and its explicitly selected positions as one audited operation."""
    area = form.save(commit=False)
    selected_ids = {position.pk for position in form.cleaned_data["positions"]}
    positions = list(Position.objects.select_for_update().filter(
        Q(pk__in=selected_ids) | Q(area_id=area.pk)
    ).order_by("pk"))
    for position in positions:
        if position.pk in selected_ids and position.area_id not in (None, area.pk):
            raise ValidationError(
                f"El puesto {position.title} acaba de vincularse a otra área. Recargue el formulario."
            )
    if area._state.adding:
        area.created_by = actor
    area.updated_by = actor
    area.full_clean()
    area.save()
    for position in positions:
        target = area if position.pk in selected_ids else None
        if position.area_id != (target.pk if target else None):
            position.area = target
            position.updated_by = actor
            position.save(update_fields=("area", "updated_by", "updated_at"))
    return area


def sync_user_organization(user_id, *, clear_if_unassigned=False):
    """Keep legacy profile text in sync with the primary assignment only."""
    user = get_user_model().objects.get(pk=user_id)
    assignments = PositionAssignment.objects.filter(user_id=user_id)
    primary = assignments.filter(is_primary=True, end_date__isnull=True).select_related(
        "position__area"
    ).first()
    if primary is None and not clear_if_unassigned and not assignments.filter(is_primary=True).exists():
        return  # A legacy user without primary assignments keeps their imported text.
    values = {
        "position": primary.position.title if primary else "",
        "area": primary.position.area.name if primary and primary.position.area_id else "",
    }
    changed = []
    for name, value in values.items():
        # The canonical title/name stays complete; legacy account fields are shorter.
        value = value[:user._meta.get_field(name).max_length]
        if getattr(user, name) != value:
            setattr(user, name, value)
            changed.append(name)
    if changed:
        user.save(update_fields=(*changed, "updated_at"))


@transaction.atomic
def assign_user_to_position(
    *,
    assignment,
    actor=None,
):
    user = get_user_model().objects.select_for_update().get(pk=assignment.user_id)
    assignment.position = Position.objects.select_for_update().get(pk=assignment.position_id)
    if not assignment.position.is_active:
        raise ValidationError("Seleccione un puesto activo.")

    if assignment.is_primary:
        previous = PositionAssignment.objects.filter(
            user=user,
            end_date__isnull=True,
            is_primary=True,
        ).exclude(pk=assignment.pk)
        for current in previous:
            if current.start_date > assignment.start_date:
                raise ValidationError("La nueva asignación no puede empezar antes de la asignación vigente.")
            current.end_date = assignment.start_date
            current.updated_by = actor
            current.save(update_fields=("end_date", "updated_by", "updated_at"))

    assignment.created_by = (
        actor
        if assignment._state.adding
        else assignment.created_by
    )
    assignment.updated_by = actor
    assignment.full_clean()
    assignment.save()

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
