
import mimetypes

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.shortcuts import get_object_or_404, render

from apps.controls.models import Control

from .product_contexts import (
    control_detail_context,
    document_preview_context,
    report_center_context,
    user_profile_context,
)
from .selectors import (
    get_annex_context,
    get_artifact_file,
    get_clause_context,
    get_clause_menu,
    get_document_context,
    get_mockup_dashboard_context,
)
from .smart_workbook import get_smart_dashboard_context
from .spreadsheet import read_xlsx_preview
from .user_profile_v67 import get_user_profile_context

from .workbench import (
    entity_detail_view,
    entity_form_view,
    entity_list_view,
    organization_context,
)


def _base_context():
    return {"clause_menu": get_clause_menu()}


@login_required
def dashboard(request):
    context = _base_context()
    context.update(get_mockup_dashboard_context())
    return render(request, "dashboard/mockup_dashboard.html", context)


@login_required
def report_center(request):
    context = _base_context()
    context.update(report_center_context())
    return render(request, "dashboard/report_center.html", context)


@login_required
def clause_detail(request, code):
    normalized = (code or "").strip().rstrip(".")
    clause = get_clause_context(normalized)
    if clause is None:
        raise Http404("Cláusula no encontrada.")
    context = _base_context()
    context["clause"] = clause
    return render(request, "dashboard/clause_detail.html", context)


@login_required
def annex_controls(request):
    context = _base_context()
    context["annex"] = get_annex_context()
    return render(request, "dashboard/annex_controls.html", context)


@login_required
def document_detail(request, document_id):
    payload = document_preview_context(document_id)
    if payload is None:
        raise Http404("Documento no encontrado.")
    context = _base_context()
    context.update(payload)
    return render(request, "dashboard/document_detail.html", context)


@login_required
def control_detail(request, pk):
    context = _base_context()
    context.update(control_detail_context(pk))
    return render(request, "dashboard/control_detail.html", context)


@login_required
def user_profile(request, pk):
    context = _base_context()
    context.update(
        get_user_profile_context(pk)
    )
    return render(
        request,
        "dashboard/user_profile.html",
        context,
    )


@login_required
@xframe_options_sameorigin
def artifact_view(request, artifact_id):
    artifact = get_artifact_file(artifact_id)
    if artifact is None:
        raise Http404("Archivo no encontrado.")
    content_type = artifact.mime_type or mimetypes.guess_type(artifact.original_name)[0] or "application/octet-stream"
    handle = artifact.file.open("rb")
    response = FileResponse(handle, content_type=content_type, as_attachment=False, filename=artifact.original_name)
    if (artifact.extension or "").lower() == "pdf":
        response["Content-Disposition"] = f'inline; filename="{artifact.original_name}"'
    return response


@login_required
def artifact_download(request, artifact_id):
    artifact = get_artifact_file(artifact_id)
    if artifact is None:
        raise Http404("Archivo no encontrado.")
    handle = artifact.file.open("rb")
    return FileResponse(handle, as_attachment=True, filename=artifact.original_name)


@login_required
def artifact_table(request, artifact_id):
    artifact = get_artifact_file(artifact_id)
    if artifact is None:
        raise Http404("Archivo no encontrado.")
    smart = get_smart_dashboard_context(artifact)
    context = _base_context()
    context["artifact"] = artifact
    if smart is not None:
        context.update(smart)
        return render(request, "dashboard/smart_workbook.html", context)
    extension = (artifact.extension or "").lower()
    if extension not in {"xlsx", "xlsm"}:
        raise Http404("Este tipo de archivo no dispone de vista tabular.")
    sheets = read_xlsx_preview(artifact.file.path, max_rows=300, max_cols=35)
    context["sheets"] = sheets
    return render(request, "dashboard/artifact_table.html", context)


@login_required
def entity_list(request, entity):
    return entity_list_view(request, entity)


@login_required
def entity_detail(request, entity, pk):
    return entity_detail_view(request, entity, pk)


@login_required
def entity_add(request, entity):
    return entity_form_view(request, entity, None)


@login_required
def entity_edit(request, entity, pk):
    return entity_form_view(request, entity, pk)


@login_required
def organization(request):
    context = _base_context()
    context.update(organization_context())
    return render(request, "dashboard/organization.html", context)


def health(request):
    return JsonResponse({"status": "ok", "service": "sgsi-siempresoft"})
