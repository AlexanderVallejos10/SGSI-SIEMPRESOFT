from datetime import date, datetime, time

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AccessReview, SystemAccess
from apps.documents.models import Document, DocumentVersion

try:
    from apps.assets.models import Asset
except Exception:
    Asset = None

try:
    from apps.incidents.models import Incident
except Exception:
    Incident = None

try:
    from apps.organization.models import PositionAssignment
except Exception:
    PositionAssignment = None


User = get_user_model()

TECHNICAL_USER_FIELDS = {
    "created_by",
    "updated_by",
    "approved_by",
    "reviewer",
    "author",
    "approver",
    "validated_by",
}


def _display(obj, field_name, default="—"):
    if obj is None:
        return default

    method = getattr(obj, f"get_{field_name}_display", None)

    if callable(method):
        try:
            value = method()
            if value not in (None, ""):
                return str(value)
        except Exception:
            pass

    value = getattr(obj, field_name, None)

    if value in (None, ""):
        return default

    return str(value)


def _friendly_user_status(user):
    raw = str(getattr(user, "status", "") or "").strip().casefold()

    if raw in {"unknown", "pending", "sin_clasificar"}:
        return "Por verificar", "pending"

    label = _display(user, "status", "Por verificar")
    normalized = label.casefold()

    if "activo" in normalized or normalized == "active":
        return label, "active"

    if (
        "inactiv" in normalized
        or "revoc" in normalized
        or "baja" in normalized
    ):
        return label, "inactive"

    return label, "pending"


def _relation_fields_to_user(model):
    if model is None:
        return []

    result = []

    for field in model._meta.fields:
        if not getattr(field, "is_relation", False):
            continue

        related_model = getattr(field.remote_field, "model", None)

        if related_model is not User:
            continue

        if field.name in TECHNICAL_USER_FIELDS:
            continue

        result.append(field.name)

    return result


def _query_related_to_user(model, user):
    if model is None:
        return []

    fields = _relation_fields_to_user(model)

    if not fields:
        return model.objects.none()

    query = Q()

    for field_name in fields:
        query |= Q(**{field_name: user})

    return model.objects.filter(query).distinct()


def _value_from_names(obj, names, default="—"):
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name, None)

            if value not in (None, ""):
                return str(value)

    return default


def _event_datetime(value):
    if value is None:
        return timezone.make_aware(
            datetime.combine(date.min, time.min)
        )

    if isinstance(value, datetime):
        if timezone.is_naive(value):
            return timezone.make_aware(value)
        return value

    if isinstance(value, date):
        return timezone.make_aware(
            datetime.combine(value, time.min)
        )

    return timezone.make_aware(
        datetime.combine(date.min, time.min)
    )


def _asset_rows(user):
    if Asset is None:
        return []

    try:
        queryset = _query_related_to_user(Asset, user).order_by("-updated_at")
    except Exception:
        return []

    rows = []

    for asset in queryset[:30]:
        rows.append(
            {
                "id": asset.pk,
                "code": _value_from_names(
                    asset,
                    ("code", "business_code", "asset_code"),
                ),
                "name": _value_from_names(
                    asset,
                    ("name", "title", "description", "asset_type"),
                ),
                "serial": _value_from_names(
                    asset,
                    ("serial_number", "serial", "inventory_number"),
                ),
                "status": _value_from_names(
                    asset,
                    ("status", "state"),
                ),
                # la ficha de activos con su trazabilidad (quién lo tuvo, salidas, revisiones, software)
                "url": reverse("assets:detail", args=[asset.code]),
            }
        )

    return rows


def _incident_rows(user):
    if Incident is None:
        return []

    try:
        queryset = _query_related_to_user(Incident, user).order_by("-updated_at")
    except Exception:
        return []

    rows = []

    for incident in queryset[:20]:
        rows.append(
            {
                "id": incident.pk,
                "code": _value_from_names(
                    incident,
                    ("code", "business_code"),
                ),
                "title": _value_from_names(
                    incident,
                    ("title", "name", "description"),
                ),
                "status": _value_from_names(
                    incident,
                    ("status", "state"),
                ),
                "url": reverse(
                    "dashboard:entity_detail",
                    kwargs={
                        "entity": "incidentes",
                        "pk": incident.pk,
                    },
                ),
            }
        )

    return rows


def _document_rows(user):
    document_ids = set()

    try:
        document_ids.update(
            Document.objects.filter(owner=user).values_list("pk", flat=True)
        )
    except Exception:
        pass

    for field in ("author", "reviewer", "approver"):
        try:
            document_ids.update(
                DocumentVersion.objects.filter(
                    **{field: user}
                ).values_list("document_id", flat=True)
            )
        except Exception:
            pass

    documents = Document.objects.filter(
        pk__in=document_ids
    ).order_by("code")

    rows = []

    for document in documents[:30]:
        roles = []

        if getattr(document, "owner_id", None) == user.pk:
            roles.append("Responsable")

        try:
            versions = document.versions.filter(
                Q(author=user)
                | Q(reviewer=user)
                | Q(approver=user)
            )

            if versions.filter(author=user).exists():
                roles.append("Autor")

            if versions.filter(reviewer=user).exists():
                roles.append("Revisor")

            if versions.filter(approver=user).exists():
                roles.append("Aprobador")
        except Exception:
            pass

        rows.append(
            {
                "code": document.code,
                "title": document.title,
                "roles": ", ".join(dict.fromkeys(roles)) or "Relacionado",
                "status": _display(document, "status", "—"),
                "url": reverse(
                    "dashboard:document_detail",
                    args=[document.pk],
                ),
            }
        )

    return rows


def _organization_context(user):
    result = {
        "current_assignment": None,
        "position": None,
        "area": None,
        "manager": None,
        "history": [],
    }

    if PositionAssignment is None:
        return result

    try:
        assignments = list(
            PositionAssignment.objects
            .filter(user=user)
            .select_related(
                "position",
                "position__area",
                "position__parent",
            )
            .order_by("-start_date", "-created_at")
        )
    except Exception:
        return result

    current = next(
        (
            item
            for item in assignments
            if item.end_date is None
            and item.is_primary
        ),
        None,
    )

    if current:
        result["current_assignment"] = current
        result["position"] = current.position
        result["area"] = current.position.area
        result["manager"] = current.position.parent

    result["history"] = assignments
    return result


def _access_context(user):
    accesses = list(
        SystemAccess.objects
        .filter(user=user)
        .select_related("system", "approved_by")
        .order_by("-authorization_date", "-updated_at")
    )

    reviews = list(
        AccessReview.objects
        .filter(access__user=user)
        .select_related(
            "access",
            "access__system",
            "reviewer",
        )
        .order_by("-reviewed_at", "-updated_at")
    )

    active_count = sum(
        1
        for item in accesses
        if str(getattr(item, "status", "")).casefold() == "active"
    )

    unknown_count = sum(
        1
        for item in accesses
        if str(getattr(item, "status", "")).casefold() in {"unknown", ""}
    )

    privileged_count = sum(
        1
        for item in accesses
        if getattr(item, "is_privileged", False)
    )

    mfa_count = sum(
        1
        for item in accesses
        if getattr(item, "mfa_enabled", False)
    )

    today = timezone.localdate()

    review_due = sum(
        1
        for item in accesses
        if getattr(item, "next_review_at", None)
        and item.next_review_at <= today
        and str(getattr(item, "status", "")).casefold() != "revoked"
    )

    rows = []

    for item in accesses:
        rows.append(
            {
                "obj": item,
                "code": item.business_code,
                "system": str(item.system),
                "role": item.role_profile or "—",
                "level": item.access_level or "—",
                "status": _display(item, "status", "—"),
                "mfa": (
                    "Sí"
                    if item.mfa_enabled
                    else (
                        "No"
                        if item.mfa_enabled is not None
                        else "Sin dato"
                    )
                ),
                "authorized": item.authorization_date,
                "last_review": item.last_review_at,
                "next_review": item.next_review_at,
                "url": reverse(
                    "dashboard:entity_detail",
                    kwargs={
                        "entity": "accesos",
                        "pk": item.pk,
                    },
                ),
            }
        )

    return {
        "objects": accesses,
        "rows": rows,
        "reviews": reviews,
        "active_count": active_count,
        "unknown_count": unknown_count,
        "privileged_count": privileged_count,
        "mfa_count": mfa_count,
        "review_due": review_due,
    }


def _timeline(user, access_ctx, organization_ctx):
    events = []

    for assignment in organization_ctx["history"]:
        events.append(
            {
                "sort_date": _event_datetime(assignment.start_date),
                "date": assignment.start_date,
                "category": "Organización",
                "title": f"Asignación a {assignment.position.title}",
                "detail": (
                    assignment.position.area.name
                    if assignment.position.area_id
                    else ""
                ),
            }
        )

        if assignment.end_date:
            events.append(
                {
                    "sort_date": _event_datetime(assignment.end_date),
                    "date": assignment.end_date,
                    "category": "Organización",
                    "title": (
                        "Fin de asignación en "
                        f"{assignment.position.title}"
                    ),
                    "detail": "",
                }
            )

    for access in access_ctx["objects"]:
        event_date = access.authorization_date or access.created_at

        events.append(
            {
                "sort_date": _event_datetime(event_date),
                "date": event_date,
                "category": "Accesos",
                "title": f"Acceso registrado en {access.system}",
                "detail": (
                    access.role_profile
                    or access.access_level
                    or ""
                ),
            }
        )

        if access.revoked_at:
            events.append(
                {
                    "sort_date": _event_datetime(access.revoked_at),
                    "date": access.revoked_at,
                    "category": "Accesos",
                    "title": f"Acceso revocado en {access.system}",
                    "detail": "",
                }
            )

    for review in access_ctx["reviews"]:
        events.append(
            {
                "sort_date": _event_datetime(review.reviewed_at),
                "date": review.reviewed_at,
                "category": "Revisión",
                "title": f"Revisión de acceso {review.access.system}",
                "detail": _display(review, "decision", ""),
            }
        )

    events.sort(
        key=lambda item: item["sort_date"],
        reverse=True,
    )

    return events[:50]


def get_user_profile_context(user_id):
    user = User.objects.get(pk=user_id)

    organization_ctx = _organization_context(user)
    access_ctx = _access_context(user)
    assets = _asset_rows(user)
    incidents = _incident_rows(user)
    documents = _document_rows(user)

    status_label, status_class = _friendly_user_status(user)

    groups = list(
        user.groups
        .order_by("name")
        .values_list("name", flat=True)
    )

    current_position = organization_ctx["position"]

    area_name = "—"
    position_name = getattr(user, "position", "") or "—"
    manager_name = "—"

    if current_position:
        position_name = current_position.title

        if current_position.area_id:
            area_name = current_position.area.name

        if current_position.parent_id:
            manager = current_position.parent

            current_manager = (
                manager.assignments
                .filter(
                    end_date__isnull=True,
                    is_primary=True,
                )
                .select_related("user")
                .first()
            )

            manager_name = (
                current_manager.user.get_full_name()
                if current_manager
                and current_manager.user.get_full_name()
                else (
                    current_manager.user.username
                    if current_manager
                    else manager.title
                )
            )

    elif hasattr(user, "area"):
        area_name = getattr(user, "area", "") or "—"

    timeline = _timeline(
        user,
        access_ctx,
        organization_ctx,
    )

    return {
        "profile_user": user,
        "status_label": status_label,
        "status_class": status_class,
        "position_name": position_name,
        "area_name": area_name,
        "manager_name": manager_name,
        "groups": groups,
        "access": access_ctx,
        "assets": assets,
        "incidents": incidents,
        "documents": documents,
        "organization_history": organization_ctx["history"],
        "timeline": timeline,
        "summary": {
            "accesses": len(access_ctx["rows"]),
            "assets": len(assets),
            "documents": len(documents),
            "incidents": len(incidents),
            "review_due": access_ctx["review_due"],
        },
        "new_access_url": (
            reverse(
                "dashboard:entity_add",
                args=["accesos"],
            )
            + f"?user={user.pk}"
        ),
    }
