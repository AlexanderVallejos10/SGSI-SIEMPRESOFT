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
            "controls",
            "risks",
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

    relation_payload = [
        {
            "id": str(item.pk),
            "source": str(item.source_id),
            "target": str(item.target_id),
            "type": item.relation_type,
            "label": item.label,
        }
        for item in relations
    ]

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
