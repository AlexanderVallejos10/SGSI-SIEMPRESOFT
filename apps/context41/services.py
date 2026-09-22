import hashlib
import mimetypes
import os
import re
from pathlib import Path

from django.core.files import File
from django.db import transaction

from apps.documents.models import SourceArtifact

from .excel_parser import parse_legal_requirements
from .models import (
    ContextDocumentKind,
    ContextDocumentVersion,
    LegalRequirement,
)


def detect_version_label(filename, fallback="NUEVA"):
    name = Path(filename).stem

    patterns = [
        r"(?i)(?:^|[ _\-])V\.?\s*(\d+(?:[._]\d+){0,3})",
        r"(?i)(?:^|[ _\-])VER(?:SION)?[ _\-]*(\d+(?:[._]\d+){0,3})",
    ]

    for pattern in patterns:
        match = re.search(pattern, name)

        if match:
            return match.group(1).replace("_", ".")

    return fallback


def sha256_file(path):
    digest = hashlib.sha256()

    with open(path, "rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def sha256_uploaded(uploaded):
    digest = hashlib.sha256()

    for chunk in uploaded.chunks():
        digest.update(chunk)

    uploaded.seek(0)

    return digest.hexdigest()


def ensure_source_artifact_from_path(path):
    path = Path(path)
    checksum = sha256_file(path)

    artifact = (
        SourceArtifact.objects
        .filter(
            checksum_sha256=checksum,
            duplicate_of__isnull=True,
        )
        .first()
    )

    if artifact is None:
        artifact = SourceArtifact(
            code=(
                "SRC-CTX41-"
                + checksum[:16].upper()
            ),
            original_name=path.name,
            original_path=str(path),
            source_archive="",
            source_kind="standalone",
            extension=path.suffix.lstrip(".").lower(),
            mime_type=(
                mimetypes.guess_type(path.name)[0]
                or "application/octet-stream"
            ),
            size_bytes=path.stat().st_size,
            checksum_sha256=checksum,
            source_verified=True,
            quality_status="verified",
            quality_notes=(
                "Fuente documental real del numeral 4.1."
            ),
        )
        artifact.save()

    if not artifact.file:
        with open(path, "rb") as handle:
            artifact.file.save(
                path.name,
                File(handle),
                save=True,
            )

    return artifact


def ensure_source_artifact_from_upload(uploaded):
    checksum = sha256_uploaded(uploaded)

    artifact = (
        SourceArtifact.objects
        .filter(
            checksum_sha256=checksum,
            duplicate_of__isnull=True,
        )
        .first()
    )

    if artifact is None:
        artifact = SourceArtifact(
            code=(
                "SRC-CTX41-"
                + checksum[:16].upper()
            ),
            original_name=uploaded.name,
            original_path=uploaded.name,
            source_archive="",
            source_kind="standalone",
            extension=(
                Path(uploaded.name)
                .suffix
                .lstrip(".")
                .lower()
            ),
            mime_type=(
                getattr(
                    uploaded,
                    "content_type",
                    "",
                )
                or mimetypes.guess_type(
                    uploaded.name
                )[0]
                or "application/octet-stream"
            ),
            size_bytes=uploaded.size,
            checksum_sha256=checksum,
            source_verified=True,
            quality_status="verified",
            quality_notes=(
                "Nueva versión cargada desde el módulo 4.1."
            ),
        )
        artifact.save()

    if not artifact.file:
        uploaded.seek(0)

        artifact.file.save(
            uploaded.name,
            uploaded,
            save=True,
        )

    return artifact


def import_legal_rows(version):
    # Las filas de versiones anteriores NO se borran.
    # Solo se reemplazan las filas asociadas a ESTA misma versión,
    # lo que mantiene completamente el histórico.
    LegalRequirement.objects.filter(
        version=version
    ).delete()

    rows = parse_legal_requirements(
        version.source_artifact.file.path
    )

    LegalRequirement.objects.bulk_create(
        [
            LegalRequirement(
                version=version,
                source_row=row["source_row"],
                number=row["number"],
                requirement=row["requirement"],
                promulgated_by=row["promulgated_by"],
                location=row["location"],
                responsible=row["responsible"],
                interested_parties=row["interested_parties"],
                status=row["status"],
            )
            for row in rows
        ]
    )

    return len(rows)


@transaction.atomic
def register_version(
    *,
    document,
    artifact,
    version_label,
    notes="",
    actor=None,
):
    existing = (
        ContextDocumentVersion.objects
        .filter(
            document=document,
            checksum_sha256=artifact.checksum_sha256,
        )
        .first()
    )

    if existing:
        ContextDocumentVersion.objects.filter(
            document=document,
            is_current=True,
        ).exclude(
            pk=existing.pk
        ).update(
            is_current=False,
        )

        existing.is_current = True
        existing.version_label = (
            version_label
            or existing.version_label
        )
        existing.notes = (
            notes
            or existing.notes
        )
        existing.updated_by = actor

        existing.save(
            update_fields=(
                "is_current",
                "version_label",
                "notes",
                "updated_by",
                "updated_at",
            )
        )

        version = existing

    else:
        ContextDocumentVersion.objects.filter(
            document=document,
            is_current=True,
        ).update(
            is_current=False
        )

        version = ContextDocumentVersion.objects.create(
            document=document,
            version_label=version_label,
            source_artifact=artifact,
            original_name=artifact.original_name,
            checksum_sha256=artifact.checksum_sha256,
            is_current=True,
            notes=notes,
            created_by=actor,
            updated_by=actor,
        )

    # Para el Excel legal, cada nueva versión reimporta
    # automáticamente su contenido estructurado.
    if document.kind == ContextDocumentKind.LEGAL:
        import_legal_rows(version)

    return version
