from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from .forms import ContextVersionUploadForm
from .models import (
    ContextDocument,
    ContextDocumentKind,
)
from .services import (
    detect_version_label,
    ensure_source_artifact_from_upload,
    register_version,
)


def _can_change(request):
    return (
        request.user.is_superuser
        or request.user.has_perm(
            "context41.add_contextdocumentversion"
        )
    )


def _org_node(position):
    assignments = list(
        position.assignments
        .filter(end_date__isnull=True)
        .select_related("user")
        .order_by("-is_primary", "start_date")
    )

    children = list(
        position.children
        .filter(is_active=True)
        .select_related("area")
        .order_by("sort_order", "title")
    )

    return {
        "position": position,
        "assignments": assignments,
        "children": [
            _org_node(child)
            for child in children
        ],
        "color": position.effective_color,
    }


@login_required
def context41(request):
    documents = list(
        ContextDocument.objects
        .filter(is_active=True)
        .prefetch_related(
            "versions__source_artifact"
        )
        .order_by("sort_order")
    )

    by_kind = {
        document.kind: document
        for document in documents
    }

    for document in documents:
        document.current_version = next(
            (
                item
                for item in document.versions.all()
                if item.is_current
            ),
            None,
        )

        document.history = list(
            document.versions.all()
        )

    legal_document = by_kind.get(
        ContextDocumentKind.LEGAL
    )

    legal_rows = []
    promulgators = []
    responsibles = []
    statuses = []

    if (
        legal_document
        and legal_document.current_version
    ):
        legal_rows = list(
            legal_document
            .current_version
            .legal_requirements
            .all()
        )

        promulgators = sorted(
            {
                row.promulgated_by
                for row in legal_rows
                if row.promulgated_by
            }
        )

        responsibles = sorted(
            {
                row.responsible
                for row in legal_rows
                if row.responsible
            }
        )

        statuses = sorted(
            {
                row.status
                for row in legal_rows
                if row.status
            }
        )

    organization_roots = []

    try:
        from apps.organization.models import Position

        roots = (
            Position.objects
            .filter(
                parent__isnull=True,
                is_active=True,
            )
            .select_related("area")
            .order_by("sort_order", "title")
        )

        organization_roots = [
            _org_node(root)
            for root in roots
        ]

    except Exception:
        organization_roots = []

    return render(
        request,
        "context41/context41.html",
        {
            "documents": documents,
            "mission": by_kind.get(
                ContextDocumentKind.MISSION_FODA
            ),
            "organization_doc": by_kind.get(
                ContextDocumentKind.ORGANIZATION
            ),
            "legal_doc": legal_document,
            "legal_rows": legal_rows,
            "promulgators": promulgators,
            "responsibles": responsibles,
            "statuses": statuses,
            "organization_roots": organization_roots,
            "can_change": _can_change(request),
        },
    )


@login_required
def upload_version(request, slug):
    if not _can_change(request):
        raise PermissionDenied

    document = get_object_or_404(
        ContextDocument,
        slug=slug,
        is_active=True,
    )

    if request.method == "POST":
        form = ContextVersionUploadForm(
            request.POST,
            request.FILES,
            document=document,
        )

        if form.is_valid():
            uploaded = form.cleaned_data["file"]

            artifact = (
                ensure_source_artifact_from_upload(
                    uploaded
                )
            )

            version_label = (
                form.cleaned_data.get(
                    "version_label"
                )
                or detect_version_label(
                    uploaded.name,
                    fallback="NUEVA",
                )
            )

            register_version(
                document=document,
                artifact=artifact,
                version_label=version_label,
                notes=(
                    form.cleaned_data[
                        "notes"
                    ]
                ),
                actor=request.user,
            )

            if (
                document.kind
                == ContextDocumentKind.LEGAL
            ):
                messages.success(
                    request,
                    (
                        "Nueva versión registrada e importada. "
                        "La tabla ya muestra esta versión; "
                        "la anterior se conserva en el historial."
                    ),
                )

            elif (
                document.kind
                == ContextDocumentKind.ORGANIZATION
            ):
                messages.success(
                    request,
                    (
                        "Nuevo PDF del organigrama registrado "
                        "como versión vigente. El PDF visible "
                        "se actualizó. La jerarquía interactiva "
                        "permanece como estructura editable "
                        "independiente para evitar cambios "
                        "automáticos no validados."
                    ),
                )

            else:
                messages.success(
                    request,
                    (
                        "Nueva versión PDF registrada. "
                        "El visor ya utiliza el nuevo archivo "
                        "y la versión anterior queda en el historial."
                    ),
                )

            return redirect(
                (
                    "/sgsi/4.1/"
                    f"?open={document.slug}"
                    "&updated=1"
                )
            )

    else:
        form = ContextVersionUploadForm(
            document=document,
        )

    return render(
        request,
        "context41/upload_version.html",
        {
            "document": document,
            "form": form,
        },
    )
