"""Cada documento que exige el Manual, relacionado con lo que la empresa tiene cargado.

Solo se muestran documentos nombrados en el Manual. Si no hay un archivo de la empresa
que coincida, se indica que falta; nunca se completa con otro contenido."""

import os
import re

from django.db import transaction
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.core.choices import LifecycleStatus
from apps.documents.models import Document, DocumentVersion, SGSISection, SourceArtifact

from .document_workspace import _files_for
from .manual_sgsi import manual_documents
from .selectors import _best_reference_match, _normalize, version_label


def _context41_match(name):
    """El módulo 4.1 guarda sus propios documentos vigentes; se aprovechan si coinciden."""
    try:
        from apps.context41.models import ContextDocument
    except ImportError:
        return None
    target = _normalize(name)
    for doc in ContextDocument.objects.filter(is_active=True).prefetch_related("versions__source_artifact"):
        title = _normalize(doc.title)
        if title and (title == target or title in target or target in title):
            current = next((v for v in doc.versions.all() if v.is_current), None)
            if current is None:
                continue
            artifact = current.source_artifact
            ext = os.path.splitext(artifact.original_name)[1].lower().lstrip(".")
            try:
                context_url = reverse("context41:home")
            except NoReverseMatch:
                context_url = ""
            try:
                upload_url = reverse("context41:upload_version", args=[doc.slug])
            except NoReverseMatch:
                upload_url = context_url
            history = sorted(doc.versions.all(), key=lambda v: v.created_at, reverse=True)
            return {
                "found": True,
                "system_title": doc.title,
                "file_name": artifact.original_name,
                "type": ext.upper() or "Archivo",
                "version": current.version_label,
                "upload_url": upload_url,
                "history": [
                    {"version": v.version_label, "date": v.created_at, "status": "Vigente" if v.is_current else "Anterior", "reason": v.notes}
                    for v in history
                ],
                "sheet_path": artifact.file.path if ext in ("xlsx", "xlsm") else "",
                "view_url": reverse("dashboard:artifact_view", args=[artifact.id]) if ext == "pdf" else "",
                "table_url": reverse("dashboard:artifact_table", args=[artifact.id]) if ext in ("xlsx", "xlsm") else "",
                "download_url": reverse("dashboard:artifact_download", args=[artifact.id]),
                "manage_url": context_url,
                "manage_label": "Versiones en 4.1",
            }
    return None


def _document_payload(document):
    versions = sorted(document.versions.all(), key=lambda v: v.created_at, reverse=True)
    current = versions[0] if versions else None
    files = _files_for(current) if current else []
    main = files[0] if files else {}
    detail = reverse("dashboard:document_detail", args=[document.id])
    return {
        "found": True,
        "system_title": document.title,
        "file_name": main.get("name", ""),
        "type": (main.get("ext") or "").upper() or "Ficha",
        "version": current.version if current else "",
        "versions": len(versions),
        "view_url": main.get("view_url", ""),
        "table_url": main.get("table_url", ""),
        "download_url": main.get("download_url", ""),
        "manage_url": detail,
        "manage_label": "Ficha e historial",
        "upload_url": f"{detail}#nueva-version",
        "history": [
            {
                "version": v.version,
                "date": v.issue_date or v.created_at,
                "status": v.get_status_display() if v.status else "Sin estado",
                "reason": v.change_reason,
            }
            for v in versions
        ],
        "sheet_path": main.get("path", ""),
    }


def resolve(name, location=""):
    context = _context41_match(name)
    if context:
        return context
    labels = [name]
    if location:
        labels.append(os.path.splitext(os.path.basename(location))[0])
    for label in labels:
        match = _best_reference_match(label)
        if not match:
            continue
        if match["kind"] == "document":
            document = Document.objects.prefetch_related(
                "versions__source_artifact", "versions__representations__source_artifact"
            ).get(pk=match["id"])
            return _document_payload(document)
        artifact = SourceArtifact.objects.get(pk=match["id"])
        document = Document.objects.filter(versions__source_artifact=artifact).prefetch_related(
            "versions__source_artifact", "versions__representations__source_artifact"
        ).first()
        if document:
            return _document_payload(document)
        ext = (artifact.extension or "").lower()
        return {
            "found": True,
            "system_title": artifact.original_name,
            "file_name": artifact.original_name,
            "type": ext.upper() or "Archivo",
            "version": "",
            "view_url": reverse("dashboard:artifact_view", args=[artifact.id]) if ext == "pdf" else "",
            "table_url": reverse("dashboard:artifact_table", args=[artifact.id]) if ext in ("xlsx", "xlsm") else "",
            "download_url": reverse("dashboard:artifact_download", args=[artifact.id]),
            "register_artifact": str(artifact.id),
            "version": version_label(artifact.original_name),
            "history": [],
            "sheet_path": artifact.file.path if ext in ("xlsx", "xlsm") and artifact.file else "",
        }
    return {"found": False}


def manual_requirements(code, include_children=False):
    """[{numeral, documents:[{name, location, ...coincidencia}]}] para la página del numeral."""
    output = []
    for numeral, docs in manual_documents(code, include_children):
        items = []
        for doc in docs:
            item = {"name": doc["name"], "location": doc.get("location", "")}
            item.update(resolve(doc["name"], item["location"]))
            items.append(item)
        output.append({
            "numeral": numeral,
            "documents": items,
            "found": sum(1 for i in items if i["found"]),
        })
    return output


def _new_code(numeral):
    base = "MAN-" + re.sub(r"[^0-9]", "-", numeral).strip("-")
    n = Document.objects.filter(code__startswith=base).count() + 1
    while Document.objects.filter(code=f"{base}-{n:02d}").exists():
        n += 1
    return f"{base}-{n:02d}"


@transaction.atomic
def register_document(numeral, name, user, artifact_id=None):
    """Crea la ficha de un documento del Manual para poder versionarlo.
    Si ya hay un archivo de la empresa, queda como su primera versión."""
    document = Document.objects.create(
        code=_new_code(numeral),
        title=name,
        category="Manual del SGSI",
        created_by=user,
        updated_by=user,
    )
    section = SGSISection.objects.filter(code=numeral).first()
    if section:
        document.sgsi_sections.add(section)
    if artifact_id:
        artifact = SourceArtifact.objects.get(pk=artifact_id)
        DocumentVersion.objects.create(
            document=document,
            version=version_label(artifact.original_name) or "1.0",
            file=artifact.file.name,
            source_artifact=artifact,
            change_reason="Registrado desde el numeral " + numeral + " del Manual con el archivo existente.",
            author=user,
            issue_date=timezone.localdate(),
            status=LifecycleStatus.ACTIVE,
            created_by=user,
            updated_by=user,
        )
    return document
