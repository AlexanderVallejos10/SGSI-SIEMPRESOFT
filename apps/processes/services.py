import hashlib
import re
from pathlib import Path

from django.core.files import File
from django.db import transaction

from .models import ProcessReferenceVersion


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_uploaded(uploaded):
    digest = hashlib.sha256()
    for chunk in uploaded.chunks():
        digest.update(chunk)
    uploaded.seek(0)
    return digest.hexdigest()


def detect_version_label(filename, fallback="NUEVA"):
    stem = Path(filename).stem
    patterns = [
        r"(?i)(?:^|[ _\-])V\.?\s*(\d+(?:[._]\d+){0,3})",
        r"(?i)(?:^|[ _\-])VER(?:SION)?[ _\-]*(\d+(?:[._]\d+){0,3})",
    ]
    for pattern in patterns:
        match = re.search(pattern, stem)
        if match:
            return match.group(1).replace("_", ".")
    return fallback


@transaction.atomic
def register_reference_path(
    *,
    document,
    file_path,
    version_label,
    notes="",
    actor=None,
):
    path = Path(file_path)
    checksum = sha256_file(path)

    existing = (
        ProcessReferenceVersion.objects
        .filter(document=document, checksum_sha256=checksum)
        .first()
    )

    if existing:
        ProcessReferenceVersion.objects.filter(
            document=document,
            is_current=True,
        ).exclude(pk=existing.pk).update(is_current=False)

        existing.is_current = True
        existing.updated_by = actor
        existing.save(
            update_fields=(
                "is_current",
                "updated_by",
                "updated_at",
            )
        )
        return existing

    ProcessReferenceVersion.objects.filter(
        document=document,
        is_current=True,
    ).update(is_current=False)

    with open(path, "rb") as handle:
        version = ProcessReferenceVersion(
            document=document,
            version_label=version_label,
            original_name=path.name,
            checksum_sha256=checksum,
            notes=notes,
            is_current=True,
            created_by=actor,
            updated_by=actor,
        )
        version.file.save(
            path.name,
            File(handle),
            save=False,
        )
        version.save()

    return version


@transaction.atomic
def register_reference_upload(
    *,
    document,
    uploaded,
    version_label="",
    notes="",
    actor=None,
):
    checksum = sha256_uploaded(uploaded)

    existing = (
        ProcessReferenceVersion.objects
        .filter(document=document, checksum_sha256=checksum)
        .first()
    )

    if existing:
        ProcessReferenceVersion.objects.filter(
            document=document,
            is_current=True,
        ).exclude(pk=existing.pk).update(is_current=False)

        existing.is_current = True
        existing.updated_by = actor
        existing.save(
            update_fields=(
                "is_current",
                "updated_by",
                "updated_at",
            )
        )
        return existing

    ProcessReferenceVersion.objects.filter(
        document=document,
        is_current=True,
    ).update(is_current=False)

    version = ProcessReferenceVersion(
        document=document,
        version_label=(
            version_label
            or detect_version_label(uploaded.name)
        ),
        original_name=uploaded.name,
        checksum_sha256=checksum,
        notes=notes,
        is_current=True,
        created_by=actor,
        updated_by=actor,
    )

    uploaded.seek(0)
    version.file.save(
        uploaded.name,
        uploaded,
        save=True,
    )

    return version
