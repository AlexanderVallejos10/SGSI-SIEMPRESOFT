
import mimetypes
import os
import re
import unicodedata
from difflib import SequenceMatcher

from django.db.models import Count, Q

from apps.accounts.models import User
from apps.assets.models import Asset
from apps.controls.models import Control, ControlEvidence
from apps.controls.models_iso import ISOClause, ISORequirement
from apps.documents.models import Document, DocumentVersion, Evidence, SourceArtifact
from apps.incidents.models import Incident
from apps.risks.models import Risk


VERSION_RE = re.compile(
    r"(?i)(?:^|[\s_\-])v(?:ers(?:i[oó]n)?)?\s*[_\-]?\s*"
    r"\d+(?:[._]\d+){0,3}(?=$|[\s_\-])"
)


def _normalize(value):
    value = str(value or "")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.casefold()
    value = VERSION_RE.sub(" ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _document_aliases(document):
    aliases = {document.title}
    for version in document.versions.select_related("source_artifact").all():
        if version.source_artifact_id:
            aliases.add(os.path.splitext(version.source_artifact.original_name)[0])
        for rep in version.representations.select_related("source_artifact").all():
            aliases.add(os.path.splitext(rep.source_artifact.original_name)[0])
    return [x for x in aliases if x]


def _artifact_aliases(artifact):
    return [
        os.path.splitext(artifact.original_name)[0],
        os.path.splitext(os.path.basename(artifact.original_path or ""))[0],
    ]


def _best_reference_match(label, documents, artifacts):
    target = _normalize(label)
    if len(target) < 4:
        return None

    best = None

    for document in documents:
        for alias in _document_aliases(document):
            candidate = _normalize(alias)
            if not candidate:
                continue
            if target == candidate:
                score = 100
            elif target in candidate or candidate in target:
                score = 96
            else:
                score = round(SequenceMatcher(None, target, candidate).ratio() * 100)
            if score >= 86 and (best is None or score > best["score"]):
                best = {
                    "kind": "document",
                    "id": str(document.id),
                    "label": label,
                    "matched": document.title,
                    "score": score,
                    "is_pdf": _document_has_pdf(document),
                }

    for artifact in artifacts:
        for alias in _artifact_aliases(artifact):
            candidate = _normalize(alias)
            if not candidate:
                continue
            if target == candidate:
                score = 99
            elif target in candidate or candidate in target:
                score = 95
            else:
                score = round(SequenceMatcher(None, target, candidate).ratio() * 100)
            if score >= 88 and (best is None or score > best["score"]):
                best = {
                    "kind": "artifact",
                    "id": str(artifact.id),
                    "label": label,
                    "matched": artifact.original_name,
                    "score": score,
                    "is_pdf": (artifact.extension or "").lower() == "pdf",
                    "is_spreadsheet": (artifact.extension or "").lower() in {"xlsx", "xlsm"},
                }

    return best


def _document_has_pdf(document):
    for version in document.versions.select_related("source_artifact").all():
        if version.source_artifact_id and (version.source_artifact.extension or "").lower() == "pdf":
            return True
        for rep in version.representations.select_related("source_artifact").all():
            if (rep.source_artifact.extension or "").lower() == "pdf":
                return True
    return False


def _split_support(value):
    if not value:
        return []
    parts = re.split(r"\s*\|\s*", str(value))
    return [p.strip() for p in parts if p.strip()]


def get_mockup_dashboard_context():
    documents = Document.objects.count()
    risks = Risk.objects.count()
    incidents = Incident.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    assets = Asset.objects.count()

    recent = []
    for item in Document.objects.order_by("-updated_at")[:5]:
        recent.append({
            "date": item.updated_at,
            "activity": f"Documento actualizado: {item.title}",
            "module": "Documentos",
            "status": item.status or "pendiente",
        })
    for item in Control.objects.order_by("-updated_at")[:5]:
        recent.append({
            "date": item.updated_at,
            "activity": f"Control revisado: {item.code} {item.name}",
            "module": "Controles",
            "status": item.implementation_status,
        })
    recent = sorted(recent, key=lambda x: x["date"], reverse=True)[:6]

    alerts = []
    controls_without_docs = (
        Control.objects
        .annotate(
            linked=Count(
                "document_assignments",
                filter=Q(document_assignments__is_active=True),
                distinct=True,
            )
        )
        .filter(linked=0)
        .order_by("code")[:4]
    )
    for control in controls_without_docs:
        alerts.append({
            "type": "control",
            "description": f"{control.code} sin documento sustentatorio automático",
            "level": "media",
        })

    pending_evidence = ControlEvidence.objects.filter(validated_at__isnull=True).count()
    if pending_evidence:
        alerts.append({
            "type": "evidence",
            "description": f"{pending_evidence} evidencias vinculadas pendientes de validación",
            "level": "alta",
        })

    draft_docs = Document.objects.filter(status="draft").count()
    if draft_docs:
        alerts.append({
            "type": "document",
            "description": f"{draft_docs} documentos en borrador",
            "level": "media",
        })

    return {
        "kpis": {
            "documents": documents,
            "risks": risks,
            "incidents": incidents,
            "active_users": active_users,
            "assets": assets,
        },
        "recent": recent,
        "alerts": alerts[:6],
        "risk_levels": {
            "very_high": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "very_low": 0,
        },
        "risk_heatmap": [[0 for _ in range(5)] for _ in range(5)],
    }


def get_clause_menu():
    titles = {
        "4": "Contexto de la organización",
        "5": "Liderazgo",
        "6": "Planificación",
        "7": "Soporte",
        "8": "Operación",
        "9": "Evaluación del desempeño",
        "10": "Mejora",
    }
    menu = []
    for root, title in titles.items():
        children = list(
            ISOClause.objects
            .filter(code__startswith=f"{root}.", active=True)
            .order_by("code")
            .values("code", "title")
        )
        # solo primer nivel en el menú; niveles más profundos aparecen en la página
        children = [
            x for x in children
            if x["code"].count(".") == 1
        ]
        menu.append({"code": root, "title": title, "children": children})
    return menu


def get_clause_context(code):
    code = str(code or "").strip().rstrip(".")
    documents = list(
        Document.objects
        .prefetch_related("versions__source_artifact", "versions__representations__source_artifact")
        .all()
    )
    artifacts = list(
        SourceArtifact.objects
        .filter(duplicate_of__isnull=True, source_verified=True)
        .exclude(file="")
        .only("id", "original_name", "original_path", "extension")
    )

    exact = ISOClause.objects.filter(code=code, active=True).first()
    if exact is None:
        exact = ISOClause.objects.filter(code__startswith=f"{code}.", active=True).order_by("code").first()

    if exact is None:
        return None

    if "." not in code:
        clause_qs = ISOClause.objects.filter(
            Q(code=code) | Q(code__startswith=f"{code}."),
            active=True,
        ).order_by("code")
    else:
        clause_qs = ISOClause.objects.filter(
            Q(code=code) | Q(code__startswith=f"{code}."),
            active=True,
        ).order_by("code")

    groups = []
    for clause in clause_qs:
        rows = []
        requirements = (
            ISORequirement.objects
            .filter(clause=clause)
            .order_by("source_row")
        )
        for req in requirements:
            if req.is_clause_heading:
                continue
            support_items = []
            for label in _split_support(req.supporting_reference):
                match = _best_reference_match(label, documents, artifacts)
                support_items.append({
                    "label": label,
                    "match": match,
                })
            rows.append({
                "label": req.source_label,
                "description": req.description,
                "support": support_items,
                "id": str(req.id),
                "source_row": req.source_row,
            })

        # la fila/cláusula se mantiene aunque no tenga detalle
        groups.append({
            "code": clause.code,
            "title": clause.title,
            "rows": rows,
        })

    return {
        "root": str(code),
        "title": exact.title if exact.code == code else f"Cláusula {code}",
        "groups": groups,
        "requirement_count": sum(len(g["rows"]) for g in groups),
    }


def get_annex_context():
    controls = (
        Control.objects
        .select_related("framework", "owner")
        .annotate(
            document_count=Count(
                "document_assignments",
                filter=Q(document_assignments__is_active=True),
                distinct=True,
            ),
            evidence_count=Count("evidence_links", distinct=True),
            validated_count=Count(
                "evidence_links",
                filter=Q(evidence_links__validated_at__isnull=False),
                distinct=True,
            ),
        )
        .order_by("code")
    )

    domains = [
        ("5", "A.5 Organizacionales"),
        ("6", "A.6 Personas"),
        ("7", "A.7 Físicos"),
        ("8", "A.8 Tecnológicos"),
    ]
    by_domain = []
    for prefix, label in domains:
        items = [c for c in controls if c.code.startswith(prefix + ".")]
        by_domain.append({
            "prefix": prefix,
            "label": label,
            "count": len(items),
            "items": items,
        })

    implemented = controls.filter(implementation_status="implemented").count()
    in_progress = controls.filter(implementation_status="in_progress").count()
    pending = controls.filter(implementation_status="pending").count()
    not_applicable = controls.filter(applicability="not_applicable").count()

    return {
        "total": controls.count(),
        "implemented": implemented,
        "in_progress": in_progress,
        "pending": pending,
        "not_applicable": not_applicable,
        "domains": by_domain,
        "controls": controls,
    }


def get_document_context(document_id):
    document = (
        Document.objects
        .prefetch_related(
            "sgsi_sections",
            "versions__source_artifact",
            "versions__representations__source_artifact",
            "control_assignments__control",
        )
        .filter(pk=document_id)
        .first()
    )
    if document is None:
        return None

    versions = []
    for version in document.versions.order_by("-created_at"):
        files = []
        if version.source_artifact_id and version.source_artifact.file:
            files.append({
                "artifact_id": str(version.source_artifact.id),
                "name": version.source_artifact.original_name,
                "extension": version.source_artifact.extension,
                "is_pdf": (version.source_artifact.extension or "").lower() == "pdf",
                "primary": True,
            })
        for rep in version.representations.all():
            artifact = rep.source_artifact
            if artifact.file and not any(x["artifact_id"] == str(artifact.id) for x in files):
                files.append({
                    "artifact_id": str(artifact.id),
                    "name": artifact.original_name,
                    "extension": artifact.extension,
                    "is_pdf": (artifact.extension or "").lower() == "pdf",
                    "primary": rep.is_primary,
                })
        versions.append({
            "version": version.version,
            "status": version.status or "pendiente",
            "files": files,
        })

    controls = [
        row.control
        for row in document.control_assignments.filter(is_active=True).select_related("control").order_by("control__code")
    ]

    return {
        "document": document,
        "versions": versions,
        "controls": controls,
        "sections": list(document.sgsi_sections.order_by("sort_order", "code")),
    }


def get_artifact_file(artifact_id):
    return (
        SourceArtifact.objects
        .filter(pk=artifact_id, source_verified=True)
        .exclude(file="")
        .first()
    )
