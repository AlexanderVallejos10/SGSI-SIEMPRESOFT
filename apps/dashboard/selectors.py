
import mimetypes
import os
import re
import unicodedata
from difflib import SequenceMatcher

from django.db.models import Count, Q, Max
from django.urls import reverse

from apps.accounts.models import User
from apps.assets.models import Asset
from apps.controls.models import Control, ControlEvidence
from apps.controls.models_iso import ISOClause, ISORequirement
from apps.documents.models import Document, DocumentVersion, Evidence, SourceArtifact
from apps.incidents.models import Incident
from apps.risks.models import Risk

from .manual_sgsi import manual_for, manual_meta


VERSION_RE = re.compile(
    r"(?i)(?:^|[\s_\-])v(?:ers(?:i[oó]n)?)?\.?\s*[_\-]?\s*"
    r"\d+(?:[._]\d+){0,3}(?=$|[\s_\-.(])"
)
# Palabras y marcas que no forman parte del nombre del documento.
NOISE_RE = re.compile(r"(?i)\b(borrador|draft|copia|final|vigente)\b|\(\s*\d+\s*\)")
RANK_RE = re.compile(r"(?i)(?:^|[\s_\-])v(?:ers(?:i[oó]n)?)?\.?\s*[_\-]?\s*(\d+(?:[._]\d+){0,3})")


def version_rank(name):
    """Número de versión escrito en el nombre (V0.10 → (0, 10)). Sirve para preferir el archivo más reciente."""
    # Solo se quita una extensión real (.pdf, .xlsx); en "V0.9" el ".9" es parte de la versión.
    found = RANK_RE.findall(re.sub(r"\.[A-Za-z]{2,5}$", "", str(name or "")))
    if not found:
        return ()
    return tuple(int(x) for x in re.split(r"[._]", found[-1]) if x.isdigit())


def version_label(name):
    rank = version_rank(name)
    return ".".join(str(x) for x in rank) if rank else ""


def _normalize(value):
    value = str(value or "")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.casefold()
    value = VERSION_RE.sub(" ", value)
    value = NOISE_RE.sub(" ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _document_aliases(document):
    # Sin select_related: así se usan los datos precargados y no hay una consulta por documento.
    aliases = {document.title}
    for version in document.versions.all():
        if version.source_artifact_id and version.source_artifact:
            aliases.add(os.path.splitext(version.source_artifact.original_name)[0])
        for rep in version.representations.all():
            if rep.source_artifact:
                aliases.add(os.path.splitext(rep.source_artifact.original_name)[0])
    return [x for x in aliases if x]


def _artifact_aliases(artifact):
    return [
        os.path.splitext(artifact.original_name)[0],
        os.path.splitext(os.path.basename(artifact.original_path or ""))[0],
    ]


def _document_has_pdf(document):
    for version in document.versions.all():
        if version.source_artifact_id and version.source_artifact and (version.source_artifact.extension or "").lower() == "pdf":
            return True
        for rep in version.representations.all():
            if rep.source_artifact and (rep.source_artifact.extension or "").lower() == "pdf":
                return True
    return False


def _document_pdf_artifact(document):
    for version in document.versions.all():
        if version.source_artifact_id and version.source_artifact and (version.source_artifact.extension or "").lower() == "pdf":
            return str(version.source_artifact_id)
        for rep in version.representations.all():
            if rep.source_artifact and (rep.source_artifact.extension or "").lower() == "pdf":
                return str(rep.source_artifact.id)
    return None


_INDEX_CACHE = {"key": None, "entries": None, "matches": {}}


def _reference_index():
    """Nombres normalizados de documentos y archivos, calculados una vez y reutilizados
    mientras no cambien los documentos ni los archivos cargados."""
    doc_stamp = Document.objects.aggregate(n=Count("id"), last=Max("updated_at"))
    art_qs = SourceArtifact.objects.filter(duplicate_of__isnull=True, source_verified=True).exclude(file="")
    art_stamp = art_qs.aggregate(n=Count("id"), last=Max("updated_at"))
    key = (doc_stamp["n"], str(doc_stamp["last"]), art_stamp["n"], str(art_stamp["last"]))
    if _INDEX_CACHE["key"] == key:
        return _INDEX_CACHE["entries"], _INDEX_CACHE["matches"]

    entries = []
    documents = Document.objects.prefetch_related(
        "versions__source_artifact", "versions__representations__source_artifact"
    )
    for document in documents:
        info = {
            "kind": "document",
            "id": str(document.id),
            "matched": document.title,
            "is_pdf": _document_has_pdf(document),
            "pdf_id": _document_pdf_artifact(document),
            "is_spreadsheet": False,
        }
        for alias in _document_aliases(document):
            normalized = _normalize(alias)
            if normalized:
                entries.append((normalized, info, 100, 96, 86))
    for artifact in art_qs.only("id", "original_name", "original_path", "extension"):
        ext = (artifact.extension or "").lower()
        info = {
            "kind": "artifact",
            "id": str(artifact.id),
            "matched": artifact.original_name,
            "is_pdf": ext == "pdf",
            "pdf_id": str(artifact.id) if ext == "pdf" else None,
            "is_spreadsheet": ext in {"xlsx", "xlsm"},
            "rank": version_rank(artifact.original_name),
        }
        for alias in _artifact_aliases(artifact):
            normalized = _normalize(alias)
            if normalized:
                entries.append((normalized, info, 99, 95, 88))
    _INDEX_CACHE.update(key=key, entries=entries, matches={})
    return entries, _INDEX_CACHE["matches"]


def _best_reference_match(label, documents=None, artifacts=None):
    target = _normalize(label)
    if len(target) < 4:
        return None
    entries, memo = _reference_index()
    if target in memo:
        return memo[target] and {**memo[target], "label": label}

    best = None
    matcher = SequenceMatcher(None, target, "")
    for candidate, info, exact, contains, minimum in entries:
        if target == candidate:
            score = exact
        elif target in candidate or candidate in target:
            score = contains
        else:
            matcher.set_seq2(candidate)
            # Descartes rápidos antes del cálculo completo.
            if matcher.real_quick_ratio() * 100 < minimum or matcher.quick_ratio() * 100 < minimum:
                continue
            score = round(matcher.ratio() * 100)
        if score < minimum:
            continue
        # A igual puntaje gana la ficha de documento y, entre archivos sueltos, la versión más alta (V0.10 antes que V0.9).
        if best is None or score > best["score"] or (
            score == best["score"] and info["kind"] == best["kind"] == "artifact" and info.get("rank", ()) > best.get("rank", ())
        ):
            best = {**info, "score": score}
    memo[target] = best
    return best and {**best, "label": label}


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
    documents = artifacts = None
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
                "has_evidence": any(item["match"] for item in support_items),
                "has_support": bool(support_items),
                "id": str(req.id),
                "source_row": req.source_row,
            })

        # la fila/cláusula se mantiene aunque no tenga detalle
        groups.append({
            "code": clause.code,
            "title": clause.title,
            "rows": rows,
            "linked": sum(1 for r in rows if r["has_evidence"]),
            "manual": manual_for(clause.code),
        })

    return {
        "root": str(code),
        "title": exact.title if exact.code == code else f"Cláusula {code}",
        "groups": groups,
        "requirement_count": sum(len(g["rows"]) for g in groups),
        "linked_count": sum(g["linked"] for g in groups),
        "manual": manual_for(code),
    }


SUBITEM_RE = re.compile(r"^\d+\)")


def _clause_code(label):
    return str(label or "").strip().rstrip(".")


def _manual_nearest(code):
    parts = code.split(".")
    while parts:
        info = manual_for(".".join(parts))
        if info:
            return info
        parts.pop()
    return None


def _support_payload(label):
    match = _best_reference_match(label)
    item = {"label": label, "found": bool(match)}
    if not match:
        return item
    item.update(name=match["matched"], kind=match["kind"])
    if match.get("pdf_id"):
        item["view_url"] = reverse("dashboard:artifact_view", args=[match["pdf_id"]])
        item["download_url"] = reverse("dashboard:artifact_download", args=[match["pdf_id"]])
    if match["kind"] == "document":
        item["detail_url"] = reverse("dashboard:document_detail", args=[match["id"]])
        item["type"] = "PDF" if match.get("is_pdf") else "Ficha"
    else:
        item["download_url"] = reverse("dashboard:artifact_download", args=[match["id"]])
        item["type"] = "PDF" if match.get("is_pdf") else ("XLSX" if match.get("is_spreadsheet") else "Archivo")
        if match.get("is_spreadsheet"):
            item["table_url"] = reverse("dashboard:artifact_table", args=[match["id"]])
    return item


def _section_documents(codes):
    """Documentos que el sistema tiene asignados a cada sección del Manual (Document.sgsi_sections)."""
    from apps.documents.models import SGSISection

    result = {code: [] for code in codes}
    documents = (
        Document.objects.filter(sgsi_sections__code__in=codes)
        .prefetch_related("sgsi_sections", "versions__source_artifact")
        .distinct()
        .order_by("title")
    )
    for document in documents:
        versions = sorted(document.versions.all(), key=lambda v: v.created_at, reverse=True)
        latest = versions[0] if versions else None
        name = ""
        if latest is not None:
            name = latest.source_artifact.original_name if latest.source_artifact_id and latest.source_artifact else latest.file.name
        ext = os.path.splitext(name or "")[1].lower().lstrip(".")
        item = {
            "title": document.title,
            "code": document.code,
            "url": reverse("dashboard:document_detail", args=[document.id]),
            "version": latest.version if latest else "",
            "versions": len(versions),
            "status": document.get_status_display() if document.status else "Sin estado",
            "type": {"pdf": "PDF", "xlsx": "XLSX", "xlsm": "XLSX", "docx": "DOCX", "doc": "DOCX"}.get(ext, "Ficha"),
        }
        for section in document.sgsi_sections.all():
            if section.code in result:
                result[section.code].append(item)
    return result


def get_clause_matrix(code):
    """La matriz de VerificacionNorma tal como está en el Excel: filas de sección
    (4., 4.1., 6.1.2.) con su documento si lo tienen, requisitos a), b) y subpuntos 1), 2)."""
    code = str(code or "").strip().rstrip(".")
    root = ISOClause.objects.filter(code=code, active=True).first()
    if root is None:
        return None
    requirements = list(
        ISORequirement.objects.filter(
            Q(clause__code=code) | Q(clause__code__startswith=f"{code}."), clause__active=True
        )
        .select_related("clause")
        .order_by("source_row")
    )

    rows = []
    section = None
    parent_item = None
    for index, req in enumerate(requirements):
        supports = [_support_payload(label) for label in _split_support(req.supporting_reference)]
        found = sum(1 for sp in supports if sp["found"])
        if req.is_clause_heading:
            kind = "section"
            section_code = _clause_code(req.source_label) or req.clause.code
            section = {"code": section_code, "title": req.description}
            parent_item = None
            path = section_code
        else:
            label = str(req.source_label or "").strip()
            kind = "subitem" if SUBITEM_RE.match(label) else "item"
            if kind == "item":
                parent_item = label.rstrip(".").rstrip(")")
                path = f"{req.clause.code} {label.rstrip('.')}"
            else:
                path = f"{req.clause.code} {parent_item or ''}{label}".strip()
            nxt = requirements[index + 1] if index + 1 < len(requirements) else None
            if kind == "item" and not supports and nxt is not None and SUBITEM_RE.match(str(nxt.source_label or "").strip()):
                kind = "group"
        if kind == "group":
            status = "group"
        elif not supports:
            status = "none"
        elif found == len(supports):
            status = "ok"
        elif found:
            status = "partial"
        else:
            status = "missing"
        clause_code = section["code"] if section else req.clause.code
        rows.append({
            "id": str(req.id),
            "kind": kind,
            "level": clause_code.count(".") if kind == "section" else None,
            "label": req.source_label,
            "path": path,
            "description": req.description,
            "supports": supports,
            "status": status,
            "section": clause_code,
            "section_title": section["title"] if section else req.clause.title,
            "manual": _manual_nearest(clause_code),
        })

    # Documentos asignados a cada sección desde la ficha del documento.
    section_codes = sorted({code} | {r["section"] for r in rows})
    linked = _section_documents(section_codes)
    for row in rows:
        row["linked"] = linked.get(row["section"], []) if row["kind"] == "section" else []

    # Resumen por subcláusula de primer nivel (4.1, 4.2...), para las tarjetas de arriba.
    overview = []
    for row in rows:
        if row["kind"] == "section" and row["section"].count(".") == code.count(".") + 1:
            overview.append({
                "code": row["section"], "title": row["description"], "total": 0, "done": 0,
                "linked": sum(len(v) for k, v in linked.items() if k == row["section"] or k.startswith(row["section"] + ".")),
            })
    for row in rows:
        if row["status"] in ("group", "none") and row["kind"] != "section":
            continue
        if row["kind"] == "section" and not row["supports"]:
            continue
        for card in overview:
            if row["section"] == card["code"] or row["section"].startswith(card["code"] + "."):
                card["total"] += 1
                card["done"] += 1 if row["status"] == "ok" else 0
    measurable = [r for r in rows if r["supports"]]
    return {
        "root": code,
        "title": root.title,
        "rows": rows,
        "overview": overview,
        "total": len(measurable),
        "done": sum(1 for r in measurable if r["status"] == "ok"),
        "manual": manual_for(code),
        "meta": manual_meta(),
        "root_linked": linked.get(code, []),
        "is_subclause": "." in code,
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
            treatment_count=Count("risk_treatments", distinct=True),
            treated_risk_count=Count("risk_treatments__risk", distinct=True),
        )
        .order_by("code")
    )
    controls = list(controls)
    for control in controls:
        # Un control que tratamientos de riesgo usan no puede figurar como "no aplicable".
        control.soa_conflict = control.applicability == "not_applicable" and control.treatment_count > 0

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

    implemented = sum(1 for c in controls if c.implementation_status == "implemented")
    in_progress = sum(1 for c in controls if c.implementation_status == "in_progress")
    pending = sum(1 for c in controls if c.implementation_status == "pending")
    not_applicable = sum(1 for c in controls if c.applicability == "not_applicable")

    return {
        "with_treatments": sum(1 for c in controls if c.treatment_count),
        "soa_conflicts": [c for c in controls if c.soa_conflict],
        "total": len(controls),
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
