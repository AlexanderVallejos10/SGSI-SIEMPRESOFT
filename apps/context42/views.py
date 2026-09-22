from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from .forms import (
    Context42VersionUploadForm,
)
from .models import (
    Context42Document,
)
from .services import (
    ensure_documents,
    legal_summary,
    party_groups,
    register_version,
)


def _can_change(
    request,
):
    return (
        request.user.is_superuser
        or request.user.has_perm(
            "context42.add_context42documentversion"
        )
    )


@login_required
def context42_home(
    request,
):
    ensure_documents()

    documents = list(
        Context42Document.objects
        .filter(
            is_active=True
        )
        .prefetch_related(
            "versions"
        )
        .order_by(
            "sort_order"
        )
    )

    by_slug = {
        doc.slug: doc
        for doc in documents
    }

    for doc in documents:
        doc.current_version = next(
            (
                version
                for version
                in doc.versions.all()
                if version.is_current
            ),
            None,
        )

        doc.history = list(
            doc.versions.all()
        )

    parties_doc = by_slug.get(
        "partes-interesadas"
    )

    legal_doc = by_slug.get(
        "requisitos-legales"
    )

    party_version = getattr(
        parties_doc,
        "current_version",
        None,
    )

    legal_version = getattr(
        legal_doc,
        "current_version",
        None,
    )

    party_group_list = (
        party_groups(
            party_version
        )
    )

    legal_rows = (
        list(
            legal_version
            .legal_rows
            .filter(
                is_active=True
            )
            .order_by(
                "source_row"
            )
        )
        if legal_version
        else []
    )

    return render(
        request,
        "context42/context42.html",
        {
            "documents":
                documents,
            "parties_doc":
                parties_doc,
            "legal_doc":
                legal_doc,
            "party_groups":
                party_group_list,
            "party_rows_count":
                (
                    party_version
                    .party_rows
                    .filter(
                        is_active=True
                    )
                    .count()
                    if party_version
                    else 0
                ),
            "party_count":
                len(
                    party_group_list
                ),
            "legal_rows":
                legal_rows,
            "legal_summary":
                legal_summary(
                    legal_version
                ),
            "can_change":
                _can_change(
                    request
                ),
        },
    )


@login_required
def upload_version(
    request,
    slug,
):
    ensure_documents()

    document = get_object_or_404(
        Context42Document,
        slug=slug,
        is_active=True,
    )

    if not _can_change(
        request
    ):
        raise PermissionDenied

    if (
        request.method
        == "POST"
    ):
        form = (
            Context42VersionUploadForm(
                request.POST,
                request.FILES,
                document=document,
            )
        )

        if form.is_valid():
            version = (
                register_version(
                    document=document,
                    uploaded_file=(
                        form.cleaned_data[
                            "file"
                        ]
                    ),
                    actor=request.user,
                    notes=(
                        form.cleaned_data
                        .get(
                            "notes",
                            "",
                        )
                    ),
                    version_label=(
                        form.cleaned_data
                        .get(
                            "version_label",
                            "",
                        )
                    ),
                )
            )

            messages.success(
                request,
                (
                    "Nueva versión registrada. "
                    "La información visible ya fue "
                    "actualizada y la versión anterior "
                    "permanece en el historial."
                ),
            )

            return redirect(
                (
                    "/sgsi/4.2/"
                    f"?open={document.slug}"
                    "&updated=1"
                )
            )

    else:
        form = (
            Context42VersionUploadForm(
                document=document
            )
        )

    return render(
        request,
        "context42/upload_version.html",
        {
            "document":
                document,
            "form":
                form,
        },
    )


@login_required
def download_current(
    request,
    slug,
):
    ensure_documents()

    document = get_object_or_404(
        Context42Document,
        slug=slug,
        is_active=True,
    )

    version = (
        document.versions
        .filter(
            is_current=True
        )
        .first()
    )

    if not version:
        raise Http404(
            "No hay archivo vigente."
        )

    return FileResponse(
        version.file.open(
            "rb"
        ),
        as_attachment=True,
        filename=(
            version.original_name
        ),
    )
