from django.db.models import Q

from .models import DocumentLink
from .services import risk_level


def risk_rows(queryset):
    rows = []
    for risk in queryset.prefetch_related("assessments", "processes", "treatments").select_related(
        "owner", "owner_position"
    ):
        assessments = list(risk.assessments.all())
        current = assessments[0] if assessments else None
        rows.append(
            {
                "risk": risk,
                "assessment": current,
                "level": risk_level(current.probability, current.impact) if current else "Pendiente",
            }
        )
    return rows


def user_links(user):
    positions = user.organization_assignments.filter(
        end_date__isnull=True, position__is_active=True
    ).values_list("position_id", flat=True)
    return (
        DocumentLink.objects.filter(is_active=True)
        .filter(Q(user=user) | Q(position_id__in=positions) | Q(all_staff=True))
        .select_related("document", "position")
    )
