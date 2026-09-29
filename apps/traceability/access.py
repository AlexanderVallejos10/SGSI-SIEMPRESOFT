from django.core.exceptions import PermissionDenied
from django.db.models import Q

from .models import DocumentLink


def can_read_document(user, document):
    if user.is_superuser:
        return True
    links = DocumentLink.objects.filter(document=document, kind="access", verified=True, is_active=True)
    positions = user.organization_assignments.filter(
        end_date__isnull=True, position__is_active=True
    ).values_list("position_id", flat=True)
    granted = links.filter(Q(user=user) | Q(position_id__in=positions) | Q(all_staff=True)).exists()
    if links.exists() or document.classification in ("restricted", "confidential"):
        return granted
    return user.has_perm("documents.view_document")


def require_document(user, document):
    if not can_read_document(user, document):
        raise PermissionDenied


def require_artifact(user, artifact):
    if user.is_superuser:
        return
    from apps.documents.models import Document

    documents = Document.objects.filter(
        Q(versions__source_artifact=artifact) | Q(versions__representations__source_artifact=artifact)
    ).distinct()
    if documents.exists():
        if not all(can_read_document(user, doc) for doc in documents):
            raise PermissionDenied
    elif not user.has_perm("documents.view_sourceartifact"):
        raise PermissionDenied
