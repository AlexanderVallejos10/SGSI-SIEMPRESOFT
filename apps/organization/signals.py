"""Synchronize existing user profile fields after organizational changes."""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import OrganizationalArea, Position, PositionAssignment
from .services import sync_user_organization


@receiver(pre_save, sender=PositionAssignment, dispatch_uid="organization_previous_assignment")
def previous_assignment(sender, instance, raw=False, **kwargs):
    if not raw and not instance._state.adding:
        instance._previous_org_assignment = sender.objects.filter(pk=instance.pk).values(
            "user_id", "is_primary"
        ).first()


@receiver(post_save, sender=PositionAssignment, dispatch_uid="organization_assignment_profile")
def assignment_profile(sender, instance, raw=False, **kwargs):
    if not raw:
        previous = getattr(instance, "_previous_org_assignment", None)
        sync_user_organization(instance.user_id, clear_if_unassigned=bool(
            instance.is_primary or (
                previous and previous["user_id"] == instance.user_id and previous["is_primary"]
            )
        ))
        if previous and previous["user_id"] != instance.user_id:
            sync_user_organization(previous["user_id"], clear_if_unassigned=previous["is_primary"])


@receiver(post_save, sender=Position, dispatch_uid="organization_position_profiles")
def position_profiles(sender, instance, raw=False, **kwargs):
    if not raw:
        for user_id in instance.assignments.filter(is_primary=True, end_date__isnull=True).values_list(
            "user_id", flat=True
        ):
            sync_user_organization(user_id)


@receiver(post_save, sender=OrganizationalArea, dispatch_uid="organization_area_profiles")
def area_profiles(sender, instance, raw=False, **kwargs):
    if not raw:
        user_ids = PositionAssignment.objects.filter(
            position__area=instance, is_primary=True, end_date__isnull=True
        ).values_list("user_id", flat=True).distinct()
        for user_id in user_ids:
            sync_user_organization(user_id)
