"""Ficha de documento: versión vigente con vista previa, historial y subida de nuevas versiones."""

import hashlib
import os
from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.core.choices import LifecycleStatus
from apps.documents.models import DocumentVersion

from .spreadsheet import read_xlsx_grid

ALLOWED = {"pdf", "xlsx", "xlsm", "docx", "doc", "pptx", "png", "jpg", "jpeg"}
MAX_BYTES = 25 * 1024 * 1024
SHEETS = {"xlsx", "xlsm"}


def _ext(name):
    return os.path.splitext(name or "")[1].lower().lstrip(".")


def version_file_adapter(version):
    """Permite servir DocumentVersion.file con la misma rutina (rangos y caché) que los artefactos."""
    return SimpleNamespace(
        pk=f"v{version.pk}",
        file=version.file,
        original_name=os.path.basename(version.file.name),
        updated_at=version.updated_at,
    )


def _files_for(version):
    files = []
    artifact = version.source_artifact if version.source_artifact_id else None
    if artifact is not None and artifact.file:
        ext = _ext(artifact.original_name)
        files.append({
            "name": artifact.original_name,
            "ext": ext,
            "view_url": reverse("dashboard:artifact_view", args=[artifact.id]) if ext == "pdf" else "",
            "table_url": reverse("dashboard:artifact_table", args=[artifact.id]) if ext in SHEETS else "",
            "download_url": reverse("dashboard:artifact_download", args=[artifact.id]),
            "path": artifact.file.path if ext in SHEETS else "",
        })
    for rep in version.representations.all():
        other = rep.source_artifact
        if other and other.file and all(f["name"] != other.original_name for f in files):
            ext = _ext(other.original_name)
            files.append({
                "name": other.original_name,
                "ext": ext,
                "view_url": reverse("dashboard:artifact_view", args=[other.id]) if ext == "pdf" else "",
                "table_url": reverse("dashboard:artifact_table", args=[other.id]) if ext in SHEETS else "",
                "download_url": reverse("dashboard:artifact_download", args=[other.id]),
                "path": other.file.path if ext in SHEETS else "",
            })
    own = version.file.name if version.file else ""
    if own and (artifact is None or os.path.basename(own) != os.path.basename(artifact.file.name or "")):
        ext = _ext(own)
        files.insert(0, {
            "name": os.path.basename(own),
            "ext": ext,
            "view_url": reverse("dashboard:version_file", args=[version.pk]) if ext == "pdf" else "",
            "table_url": reverse("dashboard:version_table", args=[version.pk]) if ext in SHEETS else "",
            "download_url": reverse("dashboard:version_download", args=[version.pk]),
            "path": version.file.path if ext in SHEETS else "",
        })
    return files


def document_workspace_context(document, user):
    versions = list(
        document.versions.select_related("source_artifact", "author", "approver")
        .prefetch_related("representations__source_artifact")
        .order_by("-created_at")
    )
    history = []
    for version in versions:
        history.append({
            "id": str(version.pk),
            "version": version.version,
            "status": version.get_status_display() if version.status else "Sin estado",
            "status_code": version.status or "none",
            "date": version.issue_date or version.created_at.date(),
            "author": (version.author.get_full_name() or version.author.username) if version.author else "",
            "reason": version.change_reason,
            "files": _files_for(version),
        })
    current = history[0] if history else None
    preview = None
    if current:
        pdf = next((f for f in current["files"] if f["view_url"]), None)
        sheet = next((f for f in current["files"] if f["table_url"]), None)
        if pdf:
            preview = {"kind": "pdf", "file": pdf}
        elif sheet:
            try:
                grids = read_xlsx_grid(sheet["path"], max_rows=60, max_cols=16)
            except (OSError, ValueError, KeyError):
                grids = []
            preview = {"kind": "sheet", "file": sheet, "sheets": grids[:6]}
        elif current["files"]:
            preview = {"kind": "file", "file": current["files"][0]}
    return {
        "document": document,
        "history": history,
        "current": current,
        "preview": preview,
        "sections": list(document.sgsi_sections.order_by("sort_order", "code")),
        "controls": [
            row.control
            for row in document.control_assignments.filter(is_active=True).select_related("control").order_by("control__code")
        ],
        "can_upload": user.is_superuser or user.has_perm("documents.add_documentversion"),
        "status_choices": [
            (LifecycleStatus.DRAFT, LifecycleStatus.DRAFT.label),
            (LifecycleStatus.REVIEW, LifecycleStatus.REVIEW.label),
            (LifecycleStatus.ACTIVE, LifecycleStatus.ACTIVE.label),
        ],
        "suggested_version": _next_version(versions[0].version if versions else ""),
    }


def _next_version(value):
    parts = str(value or "").split(".")
    if len(parts) >= 2 and parts[-1].isdigit():
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)
    return "0.1" if not value else ""


@transaction.atomic
def upload_version(document, user, uploaded, version_label, reason, status):
    version_label = (version_label or "").strip()
    reason = (reason or "").strip()
    errors = {}
    if uploaded is None:
        errors["file"] = "Adjunte el archivo de la nueva versión."
    else:
        if _ext(uploaded.name) not in ALLOWED:
            errors["file"] = "Formato no admitido. Use PDF, Excel, Word, PowerPoint o imagen."
        elif uploaded.size > MAX_BYTES:
            errors["file"] = "El archivo supera los 25 MB."
    if not version_label:
        errors["version"] = "Indique el número de versión."
    elif document.versions.filter(version=version_label).exists():
        errors["version"] = f"La versión {version_label} ya existe en este documento."
    if not reason:
        errors["reason"] = "Describa qué cambió respecto a la versión anterior."
    if status not in (LifecycleStatus.DRAFT, LifecycleStatus.REVIEW, LifecycleStatus.ACTIVE):
        status = LifecycleStatus.DRAFT
    if errors:
        raise ValidationError(errors)

    digest = hashlib.sha256()
    for chunk in uploaded.chunks():
        digest.update(chunk)
    uploaded.seek(0)

    if status == LifecycleStatus.ACTIVE:
        # Solo una versión vigente a la vez: la anterior pasa a obsoleta y queda en el historial.
        document.versions.filter(status=LifecycleStatus.ACTIVE).update(status=LifecycleStatus.OBSOLETE, updated_by=user)
    version = DocumentVersion.objects.create(
        document=document,
        version=version_label,
        file=uploaded,
        checksum_sha256=digest.hexdigest(),
        change_reason=reason,
        author=user,
        issue_date=timezone.localdate(),
        status=status,
        created_by=user,
        updated_by=user,
    )
    document.status = status if status == LifecycleStatus.ACTIVE else (document.status or status)
    document.updated_by = user
    document.save(update_fields=["status", "updated_by", "updated_at"])
    return version
