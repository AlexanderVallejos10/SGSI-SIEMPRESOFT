
from collections import OrderedDict

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.urls import reverse

from apps.accounts.models import AccessReview, SystemAccess
from apps.controls.models import Control, ControlEvidence
from apps.controls.models_linking import ControlDocumentAssignment
from apps.dashboard.models import (
    DashboardSnapshot,
    ObjectiveAlignment,
    SGSIMetric,
    SecurityObjective,
    StrategicFactor,
)
from apps.documents.models import Document
from apps.incidents.models import Incident
from apps.risks.models import Risk

from .selectors import get_document_context

User = get_user_model()


def document_preview_context(document_id):
    payload = get_document_context(document_id)
    if payload is None:
        return None

    preview = None

    for version in payload.get("versions", []):
        for file in version.get("files", []):
            ext = (file.get("extension") or "").lower()

            if ext == "pdf":
                preview = {
                    "kind": "pdf",
                    "url": reverse(
                        "dashboard:artifact_view",
                        args=[file["artifact_id"]],
                    ),
                    "download_url": reverse(
                        "dashboard:artifact_download",
                        args=[file["artifact_id"]],
                    ),
                    "file_name": file.get("name"),
                }
                break

            if ext in {"png", "jpg", "jpeg", "webp", "gif", "svg"}:
                preview = {
                    "kind": "image",
                    "url": reverse(
                        "dashboard:artifact_view",
                        args=[file["artifact_id"]],
                    ),
                    "download_url": reverse(
                        "dashboard:artifact_download",
                        args=[file["artifact_id"]],
                    ),
                    "file_name": file.get("name"),
                }
                break

            if ext in {"xlsx", "xlsm"}:
                preview = {
                    "kind": "sheet",
                    "url": reverse(
                        "dashboard:artifact_table",
                        args=[file["artifact_id"]],
                    ),
                    "download_url": reverse(
                        "dashboard:artifact_download",
                        args=[file["artifact_id"]],
                    ),
                    "file_name": file.get("name"),
                }
                break

        if preview:
            break

    payload["preview"] = preview
    return payload


def control_detail_context(control_id):
    control = get_object_or_404(Control, pk=control_id)

    assignments = (
        ControlDocumentAssignment.objects
        .filter(control=control, is_active=True)
        .select_related("document")
        .order_by("-confidence", "document__title")
    )

    document_rows = []
    seen = set()

    for item in assignments:
        document = item.document
        if document_id(document) in seen:
            continue
        seen.add(document_id(document))

        document_rows.append(
            {
                "id": document.pk,
                "code": document.code,
                "title": document.title,
                "method": item.method,
                "confidence": item.confidence,
                "url": reverse(
                    "dashboard:document_detail",
                    args=[document.pk],
                ),
            }
        )

    evidence_rows = []

    for item in (
        ControlEvidence.objects
        .filter(control=control)
        .select_related("evidence")
        .order_by("-created_at")
    ):
        evidence = item.evidence
        if evidence is None:
            continue

        evidence_rows.append(
            {
                "code": getattr(evidence, "code", "—"),
                "name": str(evidence),
                "status": (
                    "Validada"
                    if getattr(item, "validated_at", None)
                    else "Pendiente"
                ),
            }
        )

    return {
        "control": control,
        "documents": document_rows,
        "evidences": evidence_rows,
    }


def document_id(document):
    return str(document.pk)


def report_center_context():
    snapshot = (
        DashboardSnapshot.objects
        .order_by("-year", "-created_at")
        .first()
    )

    dashboard_url = ""
    if snapshot and snapshot.source_artifact_id:
        dashboard_url = reverse(
            "dashboard:artifact_table",
            args=[snapshot.source_artifact_id],
        )

    return {
        "snapshot": snapshot,
        "dashboard_url": dashboard_url,
        "cards": [
            {
                "title": "Indicadores SGSI",
                "value": (
                    SGSIMetric.objects.filter(snapshot=snapshot).count()
                    if snapshot else 0
                ),
                "note": "métricas importadas",
                "url": reverse(
                    "dashboard:entity_list",
                    args=["metricas-sgsi"],
                ),
            },
            {
                "title": "Objetivos OESI",
                "value": (
                    SecurityObjective.objects.filter(snapshot=snapshot).count()
                    if snapshot else 0
                ),
                "note": "objetivos cargados",
                "url": reverse(
                    "dashboard:entity_list",
                    args=["objetivos-oesi"],
                ),
            },
            {
                "title": "Alineamientos",
                "value": (
                    ObjectiveAlignment.objects.filter(snapshot=snapshot).count()
                    if snapshot else 0
                ),
                "note": "relaciones OEE / EPI",
                "url": reverse(
                    "dashboard:entity_list",
                    args=["alineamientos"],
                ),
            },
            {
                "title": "MEFI / MEFE",
                "value": (
                    StrategicFactor.objects.filter(snapshot=snapshot).count()
                    if snapshot else 0
                ),
                "note": "factores estratégicos",
                "url": reverse(
                    "dashboard:entity_list",
                    args=["factores-estrategicos"],
                ),
            },
            {
                "title": "Riesgos",
                "value": Risk.objects.count(),
                "note": "registro SGSI",
                "url": reverse(
                    "dashboard:entity_list",
                    args=["riesgos"],
                ),
            },
            {
                "title": "Incidentes",
                "value": Incident.objects.count(),
                "note": "seguimiento SGSI",
                "url": reverse(
                    "dashboard:entity_list",
                    args=["incidentes"],
                ),
            },
        ],
    }


def user_profile_context(user_id):
    user = get_object_or_404(User, pk=user_id)

    accesses = []
    for item in (
        SystemAccess.objects
        .filter(user=user)
        .select_related("system")
        .order_by("-updated_at")
    ):
        accesses.append(
            {
                "system": getattr(item, "system", None),
                "role": getattr(item, "role_profile", "") or "—",
                "status": getattr(item, "status", "") or "—",
            }
        )

    reviews = list(
        AccessReview.objects
        .filter(access__user=user)
        .order_by("-updated_at")[:10]
    )

    return {
        "profile_user": user,
        "accesses": accesses,
        "reviews": reviews,
    }


def organization_board_context(users):
    users = list(users)
    has_area = any((getattr(user, "area", "") or "").strip() for user in users)

    if has_area:
        grouped = OrderedDict()
        for user in sorted(
            users,
            key=lambda u: (
                getattr(u, "area", "") or "",
                getattr(u, "position", "") or "",
                u.get_full_name() or u.username,
            ),
        ):
            area = (getattr(user, "area", "") or "Sin área").strip()
            position = (getattr(user, "position", "") or "Sin puesto").strip()
            grouped.setdefault(area, OrderedDict()).setdefault(position, []).append(user)

        areas = []
        for area_name, positions in grouped.items():
            areas.append(
                {
                    "name": area_name,
                    "positions": [
                        {"name": position, "users": user_list}
                        for position, user_list in positions.items()
                    ],
                }
            )

        return {
            "mode": "areas",
            "areas": areas,
            "positions": [],
        }

    by_position = OrderedDict()
    for user in sorted(
        users,
        key=lambda u: (
            getattr(u, "position", "") or "",
            u.get_full_name() or u.username,
        ),
    ):
        position = (getattr(user, "position", "") or "Sin puesto").strip()
        by_position.setdefault(position, []).append(user)

    return {
        "mode": "positions",
        "areas": [],
        "positions": [
            {"name": position, "users": user_list}
            for position, user_list in by_position.items()
        ],
    }
