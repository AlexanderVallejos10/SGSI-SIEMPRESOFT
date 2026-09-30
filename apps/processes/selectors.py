from django.urls import reverse

from .models import (
    ProcessNode,
    ProcessReferenceDocument,
    ProcessRelation,
)


def _owner_user(process):
    user = process.current_owner_user
    if user is None:
        return None

    return {
        "id": str(user.pk),
        "name": user.get_full_name() or user.username,
        "url": reverse(
            "dashboard:user_profile",
            args=[user.pk],
        ),
    }


LEVEL_ORDER = ("Muy alto", "Alto", "Medio", "Bajo", "Muy bajo", "Pendiente")


def _risk_summary(process):
    """Riesgos del proceso por nivel, con tratamientos y controles del Anexo A."""
    from apps.risks.models import TreatmentOption
    from apps.traceability.services import risk_level

    levels = dict.fromkeys(LEVEL_ORDER, 0)
    items = []
    treatments = missing_control = 0
    annex = {
        control.code: control.name
        for control in process.controls.all()
        if control.framework_id and control.framework.code == "ISO27001-2022"
    }
    for risk in process.risks.all():
        if not risk.is_active:
            continue
        assessments = sorted(risk.assessments.all(), key=lambda a: a.assessed_at, reverse=True)
        current = assessments[0] if assessments else None
        level = risk_level(current.probability, current.impact) if current else "Pendiente"
        levels[level] += 1
        risk_treatments = list(risk.treatments.all())
        treatments += len(risk_treatments)
        for treatment in risk_treatments:
            if treatment.control_id:
                annex[treatment.control.code] = treatment.control.name
            elif treatment.option == TreatmentOption.CONTROLS:
                missing_control += 1
        items.append(
            {
                "code": risk.code,
                "event": risk.event or risk.scenario,
                "level": level,
                "type": risk.get_identification_type_display(),
                "treatments": len(risk_treatments),
                "url": reverse("traceability:risk_edit", args=[risk.pk]),
            }
        )
    items.sort(key=lambda item: (LEVEL_ORDER.index(item["level"]), item["code"]))
    return {
        "levels": levels,
        "top_level": next((name for name in LEVEL_ORDER if levels[name]), ""),
        "items": items[:8],
        "treatments": treatments,
        "missing_control": missing_control,
        "annex_controls": [
            {"code": code, "name": name}
            for code, name in sorted(annex.items(), key=lambda kv: [int(x) for x in kv[0].split(".") if x.isdigit()])
        ],
    }


def process_payload(process):
    documents = [
        {
            "id": str(document.pk),
            "code": document.code,
            "title": document.title,
            "url": reverse(
                "dashboard:document_detail",
                args=[document.pk],
            ),
        }
        for document in process.documents.all()
    ]

    outgoing = [
        {
            "id": str(item.pk),
            "process": item.target.name,
            "type": item.get_relation_type_display(),
        }
        for item in process.outgoing_relations.filter(
            is_active=True
        ).select_related("target")
    ]

    incoming = [
        {
            "id": str(item.pk),
            "process": item.source.name,
            "type": item.get_relation_type_display(),
        }
        for item in process.incoming_relations.filter(
            is_active=True
        ).select_related("source")
    ]

    return {
        "id": str(process.pk),
        "code": process.code,
        "name": process.name,
        "category": process.category.kind,
        "category_name": process.category.name,
        "kind": process.category.kind,
        "is_external": process.is_external,
        "description": process.description,
        "is_in_scope": process.is_in_scope,
        "x": process.x,
        "y": process.y,
        "owner_position": (
            process.owner_position.title
            if process.owner_position_id
            else ""
        ),
        "responsible_area": (
            process.responsible_area.name
            if process.responsible_area
            else ""
        ),
        "owner_user": _owner_user(process),
        "areas": [
            area.name
            for area in process.involved_areas.all()
        ],
        "positions": [
            position.title
            for position in process.involved_positions.all()
        ],
        "participants": [
            user.get_full_name() or user.username
            for user in process.participants.all()
        ],
        "documents": documents,
        "control_count": process.controls.count(),
        "risk_count": process.risks.filter(is_active=True).count(),
        "risk_url": reverse("traceability:risks") + f"?process={process.pk}",
        "asset_count": process.assets.count(),
        "risk_summary": _risk_summary(process),
        "incoming": incoming,
        "outgoing": outgoing,
        "edit_url": reverse(
            "processes:process_edit",
            args=[process.pk],
        ),
        "detail_url": reverse(
            "processes:process_detail",
            args=[process.pk],
        ),
        "archive_url": reverse(
            "processes:process_archive",
            args=[process.pk],
        ),
    }


def relation_json(item):
    return {
        "id": str(item.pk),
        "source": str(item.source_id),
        "target": str(item.target_id),
        "type": item.relation_type,
        "label": item.label,
        "archive_url": reverse("processes:relation_archive", args=[item.pk]),
    }


def map_context():
    processes = list(
        ProcessNode.objects
        .filter(is_active=True)
        .select_related(
            "category",
            "primary_area",
            "owner_position",
            "owner_position__area",
        )
        .prefetch_related(
            "involved_areas",
            "involved_positions",
            "participants",
            "documents",
            "controls__framework",
            "risks__assessments",
            "risks__treatments__control",
            "assets",
        )
        .order_by(
            "category__sort_order",
            "y",
            "x",
            "name",
        )
    )

    relations = list(
        ProcessRelation.objects
        .filter(
            is_active=True,
            source__is_active=True,
            target__is_active=True,
        )
        .select_related("source", "target")
    )

    payload = {
        str(process.pk): process_payload(process)
        for process in processes
    }

    relation_payload = [relation_json(item) for item in relations]

    documents = list(
        ProcessReferenceDocument.objects
        .filter(is_active=True)
        .prefetch_related("versions")
        .order_by("sort_order")
    )

    for document in documents:
        document.current_version = next(
            (
                item
                for item in document.versions.all()
                if item.is_current
            ),
            None,
        )
        document.history = list(document.versions.all())

    return {
        "processes": processes,
        "relations": relations,
        "process_payload": payload,
        "relation_payload": relation_payload,
        "reference_documents": documents,
        "scope_document": next(
            (item for item in documents if item.kind == "scope"),
            None,
        ),
        "map_document": next(
            (item for item in documents if item.kind == "map"),
            None,
        ),
    }
