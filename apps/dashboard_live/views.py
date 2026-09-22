import os
import tempfile
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .change_log import log_changes
from .exporter import export_workbook
from .forms import DashboardMetricForm, DashboardUploadForm, OesiMetricForm, StrategicFactorForm
from .importer import import_workbook
from .models import (
    DashboardCellTrace,
    DashboardChange,
    DashboardMetric,
    OeeOsiAlignment,
    OesiMetric,
    RequirementOsiAlignment,
    StrategicFactor,
)
from .selectors import build_dashboard_context, current_dataset


def _can_change(request):
    return request.user.is_superuser or request.user.has_perm("dashboard_live.change_dashboardmetric")


def _trace_lookup(dataset, entity_type, entity_key):
    return {
        item.field_name: item
        for item in DashboardCellTrace.objects.filter(
            dataset=dataset,
            entity_type=entity_type,
            entity_key=str(entity_key),
        )
    }


@login_required
def home(request):
    context = build_dashboard_context()
    context["can_change"] = _can_change(request)
    context["active_tab"] = request.GET.get("tab", "resumen")
    return render(request, "dashboard_live/home.html", context)


def _edit_model(request, *, obj, form_class, entity_type, entity_key, title, subtitle, return_url):
    if not _can_change(request):
        raise PermissionDenied

    before = {field: getattr(obj, field) for field in form_class.Meta.fields}

    if request.method == "POST":
        form = form_class(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = request.user
            obj.save()
            after = {field: getattr(obj, field) for field in form_class.Meta.fields}
            log_changes(
                dataset=obj.dataset,
                entity_type=entity_type,
                entity_key=entity_key,
                before=before,
                after=after,
                actor=request.user,
                trace_lookup=_trace_lookup(obj.dataset, entity_type, entity_key),
            )
            messages.success(
                request,
                "Cambios guardados. El Excel descargable reflejará esta actualización.",
            )
            return redirect(return_url)
    else:
        form = form_class(instance=obj)

    return render(
        request,
        "dashboard_live/edit_form.html",
        {
            "title": title,
            "subtitle": subtitle,
            "form": form,
            "return_url": return_url,
            "trace": list(
                DashboardCellTrace.objects.filter(
                    dataset=obj.dataset,
                    entity_type=entity_type,
                    entity_key=str(entity_key),
                ).order_by("source_cell")
            ),
        },
    )


@login_required
def edit_sgsi_metric(request, pk):
    metric = get_object_or_404(DashboardMetric, pk=pk, dataset__is_current=True)
    return _edit_model(
        request,
        obj=metric,
        form_class=DashboardMetricForm,
        entity_type="sgsi_metric",
        entity_key=metric.metric_id,
        title=f"Editar indicador SGSI {metric.metric_id}",
        subtitle=metric.description,
        return_url="/?tab=sgsi",
    )


@login_required
def edit_oesi_metric(request, pk):
    metric = get_object_or_404(OesiMetric, pk=pk, dataset__is_current=True)
    return _edit_model(
        request,
        obj=metric,
        form_class=OesiMetricForm,
        entity_type="oesi_metric",
        entity_key=metric.metric_id,
        title=f"Editar OESI {metric.metric_id}",
        subtitle=metric.description,
        return_url="/?tab=oesi",
    )


@login_required
def edit_factor(request, pk):
    factor = get_object_or_404(StrategicFactor, pk=pk, dataset__is_current=True)
    return _edit_model(
        request,
        obj=factor,
        form_class=StrategicFactorForm,
        entity_type="strategic_factor",
        entity_key=factor.pk,
        title=f"Editar factor {factor.matrix_type}",
        subtitle=factor.description,
        return_url=f"/?tab={factor.matrix_type.lower()}",
    )


def _next_relation(current):
    return {"": "S", "S": "P", "P": ""}.get(current, "")


def _record_alignment_change(request, alignment, entity_type, old, new):
    trace = DashboardCellTrace.objects.filter(
        dataset=alignment.dataset,
        entity_type=entity_type,
        entity_key=str(alignment.pk),
        field_name="relation",
    ).first()
    DashboardChange.objects.create(
        dataset=alignment.dataset,
        entity_type=entity_type,
        entity_key=str(alignment.pk),
        field_name="relation",
        old_value=old,
        new_value=new,
        source_sheet=trace.source_sheet if trace else "",
        source_cell=trace.source_cell if trace else alignment.source_cell,
        created_by=request.user,
        updated_by=request.user,
    )


@login_required
@require_POST
def toggle_oee_alignment(request, pk):
    if not _can_change(request):
        raise PermissionDenied
    alignment = get_object_or_404(OeeOsiAlignment, pk=pk, dataset__is_current=True)
    old = alignment.relation
    new = _next_relation(old)

    if new == "P":
        siblings = OeeOsiAlignment.objects.filter(
            dataset=alignment.dataset,
            security_objective=alignment.security_objective,
            relation="P",
        ).exclude(pk=alignment.pk)
        for sibling in siblings:
            sibling_old = sibling.relation
            sibling.relation = "S"
            sibling.updated_by = request.user
            sibling.save(update_fields=("relation", "updated_by", "updated_at"))
            _record_alignment_change(request, sibling, "oee_osi", sibling_old, "S")

    alignment.relation = new
    alignment.updated_by = request.user
    alignment.save(update_fields=("relation", "updated_by", "updated_at"))
    _record_alignment_change(request, alignment, "oee_osi", old, new)
    return JsonResponse({"ok": True, "relation": new})


@login_required
@require_POST
def toggle_req_alignment(request, pk):
    if not _can_change(request):
        raise PermissionDenied
    alignment = get_object_or_404(RequirementOsiAlignment, pk=pk, dataset__is_current=True)
    old = alignment.relation
    new = _next_relation(old)
    alignment.relation = new
    alignment.updated_by = request.user
    alignment.save(update_fields=("relation", "updated_by", "updated_at"))
    _record_alignment_change(request, alignment, "req_osi", old, new)
    return JsonResponse({"ok": True, "relation": new})


@login_required
def download_updated_workbook(request):
    dataset = current_dataset()
    if dataset is None:
        messages.error(request, "No existe un Dashboard vigente.")
        return redirect("/")

    content = export_workbook(dataset)
    filename = f"Dashboard_SGSI_SIEMPRESOFT_{dataset.version_label or 'actualizado'}.xlsx"
    response = HttpResponse(
        content,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    DashboardChange.objects.create(
        dataset=dataset,
        entity_type="export",
        entity_key=dataset.code,
        field_name="workbook",
        new_value=filename,
        created_by=request.user,
        updated_by=request.user,
    )
    return response


@login_required
def upload_workbook(request):
    if not _can_change(request):
        raise PermissionDenied

    if request.method == "POST":
        form = DashboardUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.cleaned_data["file"]
            suffix = Path(uploaded.name).suffix
            handle = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
            try:
                for chunk in uploaded.chunks():
                    handle.write(chunk)
                handle.close()
                import_workbook(
                    path=handle.name,
                    version_label=form.cleaned_data.get("version_label", ""),
                    notes=form.cleaned_data.get("notes", ""),
                    actor=request.user,
                    original_name=uploaded.name,
                    apply_changes=True,
                )
            finally:
                try:
                    os.unlink(handle.name)
                except OSError:
                    pass
            messages.success(
                request,
                "Nueva versión del Dashboard importada. La pantalla ya utiliza sus datos.",
            )
            return redirect("/")
    else:
        form = DashboardUploadForm()

    return render(request, "dashboard_live/upload.html", {"form": form})
