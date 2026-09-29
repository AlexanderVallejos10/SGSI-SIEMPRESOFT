from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404

from apps.documents.models import DocumentVersion, SourceArtifact

from .access import require_artifact, require_document
from .models import Handover, ImportBatch


@login_required
def protected_media(request, path):
    root = Path(settings.MEDIA_ROOT).resolve()
    target = (root / path).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise Http404
    if not request.user.is_superuser:
        act = Handover.objects.filter(signed_file=path).first()
        artifact = SourceArtifact.objects.filter(file=path).first()
        version = DocumentVersion.objects.filter(file=path).select_related("document").first()
        if act:
            if request.user != act.user and not request.user.has_perm("traceability.view_handover"):
                raise PermissionDenied
        elif artifact:
            require_artifact(request.user, artifact)
        elif version:
            require_document(request.user, version.document)
        elif ImportBatch.objects.filter(source=path).exists():
            if not request.user.has_perm("traceability.view_importbatch"):
                raise PermissionDenied
        else:
            # Unclassified files require explicit administrator access until an owning module provides a protected view.
            raise PermissionDenied
    return FileResponse(target.open("rb"))
