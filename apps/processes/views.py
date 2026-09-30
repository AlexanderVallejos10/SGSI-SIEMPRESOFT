import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from .forms import (
    ProcessNodeForm,
    ProcessRelationForm,
    QuickProcessForm,
    ReferenceVersionUploadForm,
)
from .models import (
    ProcessCategory,
    ProcessNode,
    ProcessReferenceDocument,
    ProcessReferenceVersion,
    ProcessRelation,
)
from .layout import free_slot
from .models import LANE_KINDS
from .selectors import map_context, process_payload, relation_json
from .services import register_reference_upload


def _can_change(request):
    return (
        request.user.is_superuser
        or request.user.has_perm(
            "processes.change_processnode"
        )
    )


@login_required
def process_map(request):
    context = map_context()
    context["show_scope"] = request.resolver_match.url_name == "context43"
    context["can_change"] = _can_change(request)
    context["quick_form"] = QuickProcessForm()
    context["relation_form"] = ProcessRelationForm()

    return render(
        request,
        "processes/map.html",
        context,
    )


@login_required
def process_create(request):
    if not _can_change(request):
        raise PermissionDenied

    if request.method == "POST":
        form = QuickProcessForm(request.POST)

        if form.is_valid():
            process = form.save(commit=False)
            process.x, process.y = free_slot(process.category)
            process.created_by = request.user
            process.updated_by = request.user
            process.full_clean()
            process.save()

            messages.success(
                request,
                "Proceso creado y agregado al mapa.",
            )

            return redirect("processes:map")
    else:
        form = QuickProcessForm()

    return render(
        request,
        "processes/process_form.html",
        {
            "form": form,
            "title": "Nuevo proceso",
            "mode": "create",
        },
    )


@login_required
def process_edit(request, pk):
    if not _can_change(request):
        raise PermissionDenied

    process = get_object_or_404(
        ProcessNode,
        pk=pk,
    )

    if request.method == "POST":
        form = ProcessNodeForm(
            request.POST,
            instance=process,
        )

        if form.is_valid():
            process = form.save(commit=False)
            if "category" in form.changed_data:
                # Al pasar a otra franja busca un lugar libre; sus relaciones se mantienen.
                process.x, process.y = free_slot(process.category, exclude_pk=process.pk)
            process.updated_by = request.user
            process.full_clean()
            process.save()
            form.save_m2m()

            messages.success(
                request,
                "Proceso actualizado.",
            )

            return redirect("processes:map")
    else:
        form = ProcessNodeForm(instance=process)

    return render(
        request,
        "processes/process_form.html",
        {
            "form": form,
            "title": f"Editar proceso: {process.name}",
            "process": process,
            "mode": "edit",
        },
    )


@login_required
def process_detail(request, pk):
    process = get_object_or_404(
        ProcessNode.objects
        .select_related(
            "category",
            "owner_position",
            "owner_position__area",
        )
        .prefetch_related(
            "involved_areas",
            "involved_positions",
            "participants",
            "documents",
            "controls",
            "risks",
            "assets",
        ),
        pk=pk,
    )

    return render(
        request,
        "processes/detail.html",
        {
            "process": process,
            "payload": process_payload(process),
            "can_change": _can_change(request),
        },
    )


@login_required
@require_POST
def process_archive(request, pk):
    if not _can_change(request):
        raise PermissionDenied

    process = get_object_or_404(
        ProcessNode,
        pk=pk,
    )

    with transaction.atomic():
        process.is_active = False
        process.updated_by = request.user
        process.save(
            update_fields=(
                "is_active",
                "updated_by",
                "updated_at",
            )
        )

        ProcessRelation.objects.filter(
            source=process,
            is_active=True,
        ).update(is_active=False)

        ProcessRelation.objects.filter(
            target=process,
            is_active=True,
        ).update(is_active=False)

    messages.success(
        request,
        (
            "El proceso fue retirado del mapa. "
            "No se eliminó físicamente."
        ),
    )

    return redirect("processes:map")


@login_required
def relation_create(request):
    if not _can_change(request):
        raise PermissionDenied

    if request.method != "POST":
        return redirect("processes:map")
    wants_json = "application/json" in request.headers.get("Accept", "")
    data = request.POST
    # Una relación retirada antes se reactiva en lugar de chocar con la restricción de unicidad.
    relation = ProcessRelation.objects.filter(
        source_id=data.get("source") or None,
        target_id=data.get("target") or None,
        relation_type=data.get("relation_type") or "flow",
        is_active=False,
    ).first()
    form = ProcessRelationForm(data, instance=relation)
    error = ""
    if data.get("source") and data.get("source") == data.get("target"):
        error = "Un proceso no puede relacionarse consigo mismo."
    elif form.is_valid():
        relation = form.save(commit=False)
        relation.is_active = True
        relation.created_by = relation.created_by or request.user
        relation.updated_by = request.user
        relation.full_clean()
        relation.save()
    else:
        error = " ".join(str(e) for errors in form.errors.values() for e in errors) or "No se pudo crear la relación."
    if wants_json:
        if error:
            return JsonResponse({"ok": False, "error": error}, status=400)
        return JsonResponse({"ok": True, "relation": relation_json(relation)})
    if error:
        messages.error(request, error)
    else:
        messages.success(request, "Relación creada.")
    return redirect("processes:map")

    form = ProcessRelationForm(request.POST)

    if form.is_valid():
        relation = form.save(commit=False)
        relation.created_by = request.user
        relation.updated_by = request.user
        relation.full_clean()
        relation.save()

        messages.success(
            request,
            "Relación creada.",
        )
    else:
        messages.error(
            request,
            "No se pudo crear la relación.",
        )

    return redirect("processes:map")


@login_required
@require_POST
def relation_archive(request, pk):
    if not _can_change(request):
        raise PermissionDenied

    relation = get_object_or_404(
        ProcessRelation,
        pk=pk,
    )

    relation.is_active = False
    relation.updated_by = request.user
    relation.save(
        update_fields=(
            "is_active",
            "updated_by",
            "updated_at",
        )
    )
    if "application/json" in request.headers.get("Accept", ""):
        return JsonResponse({"ok": True})

    messages.success(
        request,
        "Relación retirada del mapa.",
    )

    return redirect("processes:map")


@login_required
@require_POST
def save_layout(request):
    if not _can_change(request):
        raise PermissionDenied

    try:
        payload = json.loads(
            request.body.decode("utf-8")
        )
    except Exception:
        return JsonResponse(
            {
                "ok": False,
                "error": "JSON inválido.",
            },
            status=400,
        )

    moves = payload.get("moves", [])

    category_map = {
        item.kind: item
        for item in ProcessCategory.objects.filter(
            is_active=True
        )
    }

    updated = 0

    with transaction.atomic():
        for move in moves:
            try:
                process = ProcessNode.objects.get(
                    pk=move["id"],
                    is_active=True,
                )
            except (
                KeyError,
                ProcessNode.DoesNotExist,
            ):
                continue

            x = max(
                0,
                min(
                    1120,
                    int(move.get("x", process.x)),
                ),
            )
            y = max(
                0,
                min(
                    650,
                    int(move.get("y", process.y)),
                ),
            )

            category = process.category
            if move.get("category") in LANE_KINDS and process.category.kind in LANE_KINDS:
                category = category_map.get(move["category"], process.category)

            process.x = x
            process.y = y
            process.category = category
            process.updated_by = request.user
            process.full_clean()
            process.save(
                update_fields=(
                    "x",
                    "y",
                    "category",
                    "updated_by",
                    "updated_at",
                )
            )
            updated += 1

    return JsonResponse(
        {
            "ok": True,
            "updated": updated,
        }
    )


@login_required
def reference_upload(request, slug):
    if not _can_change(request):
        raise PermissionDenied

    document = get_object_or_404(
        ProcessReferenceDocument,
        slug=slug,
        is_active=True,
    )

    if request.method == "POST":
        form = ReferenceVersionUploadForm(
            request.POST,
            request.FILES,
            document=document,
        )

        if form.is_valid():
            register_reference_upload(
                document=document,
                uploaded=form.cleaned_data["file"],
                version_label=form.cleaned_data.get(
                    "version_label",
                    "",
                ),
                notes=form.cleaned_data.get(
                    "notes",
                    "",
                ),
                actor=request.user,
            )

            messages.success(
                request,
                (
                    "Nueva versión registrada. "
                    "La versión anterior permanece en el historial."
                ),
            )

            return redirect("processes:map")
    else:
        form = ReferenceVersionUploadForm(
            document=document
        )

    return render(
        request,
        "processes/reference_upload.html",
        {
            "document": document,
            "form": form,
        },
    )


@login_required
@xframe_options_sameorigin
def reference_version_view(request, pk):
    version = get_object_or_404(
        ProcessReferenceVersion,
        pk=pk,
    )

    return FileResponse(
        version.file.open("rb"),
        content_type="application/pdf",
        as_attachment=False,
        filename=version.original_name,
    )


@login_required
def reference_version_download(request, pk):
    version = get_object_or_404(
        ProcessReferenceVersion,
        pk=pk,
    )

    return FileResponse(
        version.file.open("rb"),
        as_attachment=True,
        filename=version.original_name,
    )
