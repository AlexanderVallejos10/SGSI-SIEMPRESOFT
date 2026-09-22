from django.db.models import Count, Max, OuterRef, Q, Subquery

from .models import (
    AccessReview,
    CorporateSystem,
    SystemAccess,
    User,
    UserStatus,
)


def get_user_list(
    *,
    search="",
    area="",
    status="",
):
    """
    Lista de usuarios alimentada exclusivamente
    desde PostgreSQL.

    Las métricas de accesos se calculan usando
    SystemAccess reales/documentados.
    """

    latest_review = (
        AccessReview.objects
        .filter(
            access__user=OuterRef("pk"),
        )
        .order_by("-reviewed_at")
        .values("reviewed_at")[:1]
    )

    queryset = (
        User.objects
        .select_related("manager")
        .prefetch_related("groups")
        .annotate(
            role_count=Count(
                "groups",
                distinct=True,
            ),

            systems_count=Count(
                "system_accesses__system",
                distinct=True,
            ),

            privileged_accesses_count=Count(
                "system_accesses",
                filter=Q(
                    system_accesses__is_privileged=True
                ),
                distinct=True,
            ),

            mfa_enabled_count=Count(
                "system_accesses",
                filter=Q(
                    system_accesses__mfa_enabled=True
                ),
                distinct=True,
            ),

            mfa_disabled_count=Count(
                "system_accesses",
                filter=Q(
                    system_accesses__mfa_enabled=False
                ),
                distinct=True,
            ),

            mfa_unknown_count=Count(
                "system_accesses",
                filter=Q(
                    system_accesses__mfa_enabled__isnull=True
                ),
                distinct=True,
            ),

            latest_access_evidence=Max(
                "system_accesses__status_as_of"
            ),

            last_review_date=Subquery(
                latest_review
            ),
        )
    )

    if search:
        queryset = queryset.filter(
            Q(
                business_code__icontains=search
            )
            | Q(
                username__icontains=search
            )
            | Q(
                first_name__icontains=search
            )
            | Q(
                last_name__icontains=search
            )
            | Q(
                email__icontains=search
            )
            | Q(
                document_number__icontains=search
            )
        )

    if area:
        queryset = queryset.filter(
            area=area
        )

    if status in UserStatus.values:
        queryset = queryset.filter(
            status=status
        )

    return queryset.order_by(
        "business_code"
    )


def get_user_areas():
    """
    Áreas que realmente existen en los usuarios
    almacenados.
    """

    return (
        User.objects
        .exclude(area="")
        .values_list(
            "area",
            flat=True,
        )
        .distinct()
        .order_by("area")
    )


def get_user_summary():
    """
    Resumen general calculado desde los datos
    reales existentes.

    No utiliza valores fijos de los mockups.
    """

    users = User.objects.all()
    accesses = SystemAccess.objects.all()

    confirmed_mfa = (
        accesses
        .exclude(
            mfa_enabled__isnull=True
        )
        .count()
    )

    mfa_enabled = (
        accesses
        .filter(
            mfa_enabled=True
        )
        .count()
    )

    if confirmed_mfa:
        mfa_percentage = round(
            (
                mfa_enabled
                / confirmed_mfa
            )
            * 100,
            1,
        )
    else:
        mfa_percentage = None

    return {
        "users_total": users.count(),

        "users_active": users.filter(
            status=UserStatus.ACTIVE
        ).count(),

        "users_blocked": users.filter(
            status=UserStatus.BLOCKED
        ).count(),

        "users_inactive": users.filter(
            status=UserStatus.INACTIVE
        ).count(),

        "users_unknown": users.filter(
            status=UserStatus.UNKNOWN
        ).count(),

        "systems_total": (
            CorporateSystem.objects.count()
        ),

        "accesses_total": accesses.count(),

        "privileged_accesses": (
            accesses
            .filter(
                is_privileged=True
            )
            .count()
        ),

        "mfa_confirmed": confirmed_mfa,

        "mfa_enabled": mfa_enabled,

        "mfa_percentage": mfa_percentage,

        "reviews_total": (
            AccessReview.objects.count()
        ),
    }