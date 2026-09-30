
import mimetypes
import os

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from apps.controls.models import Control

from .product_contexts import (
    control_detail_context,
    document_preview_context,
    report_center_context,
    user_profile_context,
)
from .file_serving import serve_artifact
from .selectors import (
    get_annex_context,
    get_clause_matrix,
    get_artifact_file,
    get_clause_context,
    get_clause_menu,
    get_document_context,
    get_mockup_dashboard_context,
)
from .smart_workbook import get_smart_dashboard_context
from .spreadsheet import read_xlsx_grid, read_xlsx_preview
from .user_profile import get_user_profile_context

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
    matrix = get_clause_matrix(normalized)
    if matrix is None:
        raise Http404("Cláusula no encontrada.")
    from apps.controls.models_iso import ISOClause

    from .manual_documents import manual_requirements
    from .manual_sgsi import manual_for

    required = manual_requirements(normalized, include_children=True)
    titles = dict(ISOClause.objects.filter(code__startswith=normalized.split(".")[0]).values_list("code", "title"))
    rows = matrix["rows"]
    depth = normalized.count(".") + 1
    if matrix["is_subclause"]:
        numerals = [normalized]
    else:
        numerals = [r["section"] for r in rows if r["kind"] == "section" and r["section"].count(".") == depth]
        numerals += [g["numeral"] for g in required if g["numeral"].count(".") == depth and g["numeral"] not in numerals]
        numerals.sort(key=lambda c: [int(x) for x in c.split(".") if x.isdigit()])

    from .selectors import _section_documents

    section_docs = _section_documents(numerals)

    # Una tarjeta por numeral: lo que exige el Manual y los requisitos de la norma de ese numeral.
    numeral_cards = []
    for code in numerals:
        head = next((r for r in rows if r["kind"] == "section" and r["section"] == code), None)
        norm_rows = [r for r in rows if r is not head and (r["section"] == code or r["section"].startswith(code + "."))]
        manual = [dict(g, title=titles.get(g["numeral"], "")) for g in required if g["numeral"] == code or g["numeral"].startswith(code + ".")]
        manual_docs = [d for g in manual for d in g["documents"]]
        measurable = [r for r in norm_rows if r["supports"]] + ([head] if head and head["supports"] else [])
        numeral_cards.append({
            "code": code,
            "anchor": "n-" + code.replace(".", "-"),
            "title": head["description"] if head else titles.get(code, ""),
            "head_supports": head["supports"] if head else [],
            "manual": manual,
            "manual_total": len(manual_docs),
            "manual_found": sum(1 for d in manual_docs if d["found"]),
            "norm_rows": norm_rows,
            "norm_total": len(measurable),
            "norm_done": sum(1 for r in measurable if r["status"] == "ok"),
            "linked_extra": [
                d for d in section_docs.get(code, [])
                if d["title"] not in {m.get("system_title") for m in manual_docs}
            ],
            "summary": (manual_for(code) or {}).get("summary"),
            "modules": (manual_for(code) or {}).get("modules", []),
        })
    # En un numeral, cada documento se muestra abierto como en 4.1; los Excel traen su vista previa.
    if matrix["is_subclause"]:
        from .spreadsheet import read_xlsx_grid

        for card in numeral_cards:
            for group in card["manual"]:
                for d in group["documents"]:
                    if d.get("sheet_path"):
                        try:
                            d["sheet"] = read_xlsx_grid(d["sheet_path"], max_rows=40, max_cols=12)[:4]
                        except (OSError, ValueError, KeyError):
                            d["sheet"] = []
    context = _base_context()
    context["matrix"] = matrix
    context["numeral_cards"] = numeral_cards
    context["manual_total"] = sum(c["manual_total"] for c in numeral_cards)
    context["manual_found"] = sum(c["manual_found"] for c in numeral_cards)
    context["can_register"] = request.user.is_superuser or request.user.has_perm("documents.add_document")
    from apps.accounts.security import is_sgsi_admin
    if is_sgsi_admin(request.user):
        from .manual_reference import manual_history
        context["manual_history"] = manual_history()
    return render(request, "dashboard/clause_detail.html", context)


@login_required
def register_manual_document(request):
    from django.core.exceptions import PermissionDenied
    from django.shortcuts import redirect

    from .manual_documents import register_document

    if request.method != "POST":
        raise Http404
    if not (request.user.is_superuser or request.user.has_perm("documents.add_document")):
        raise PermissionDenied
    numeral = (request.POST.get("numeral") or "").strip()
    name = (request.POST.get("name") or "").strip()
    if not numeral or not name:
        raise Http404
    document = register_document(numeral, name, request.user, request.POST.get("artifact") or None)
    url = reverse("dashboard:document_detail", args=[document.pk])
    # Sin archivo, o si se pidió subir una versión nueva, se abre directo el formulario de subida.
    wants_upload = request.POST.get("upload") or not request.POST.get("artifact")
    return redirect(url + "#nueva-version" if wants_upload else url)


@login_required
def annex_controls(request):
    context = _base_context()
    context["annex"] = get_annex_context()
    return render(request, "dashboard/annex_controls.html", context)


@login_required
def document_detail(request, document_id):
    from django.contrib import messages
    from django.core.exceptions import PermissionDenied, ValidationError
    from django.shortcuts import redirect

    from apps.documents.models import Document
    from apps.traceability.access import require_document

    from .document_workspace import document_workspace_context, upload_version

    document = get_object_or_404(Document, pk=document_id)
    require_document(request.user, document)
    errors = {}
    if request.method == "POST":
        if not (request.user.is_superuser or request.user.has_perm("documents.add_documentversion")):
            raise PermissionDenied
        try:
            version = upload_version(
                document,
                request.user,
                request.FILES.get("file"),
                request.POST.get("version"),
                request.POST.get("reason"),
                request.POST.get("status"),
            )
        except ValidationError as exc:
            errors = exc.message_dict
        else:
            messages.success(request, f"Versión {version.version} registrada. La anterior queda en el historial.")
            return redirect("dashboard:document_detail", document_id=document.pk)
    context = _base_context()
    context.update(document_workspace_context(document, request.user))
    context["upload_errors"] = errors
    context["upload_values"] = request.POST if errors else {}
    return render(request, "dashboard/document_detail.html", context, status=400 if errors else 200)


def _version_for(request, version_id):
    from apps.documents.models import DocumentVersion
    from apps.traceability.access import require_document

    version = get_object_or_404(DocumentVersion.objects.select_related("document"), pk=version_id)
    require_document(request.user, version.document)
    if not version.file:
        raise Http404("La versión no tiene archivo propio.")
    return version


@login_required
@xframe_options_sameorigin
def version_file(request, version_id):
    from .document_workspace import version_file_adapter

    version = _version_for(request, version_id)
    adapter = version_file_adapter(version)
    content_type = mimetypes.guess_type(adapter.original_name)[0] or "application/octet-stream"
    return serve_artifact(request, adapter, content_type, inline=True)


@login_required
def version_download(request, version_id):
    from .document_workspace import version_file_adapter

    version = _version_for(request, version_id)
    adapter = version_file_adapter(version)
    content_type = mimetypes.guess_type(adapter.original_name)[0] or "application/octet-stream"
    return serve_artifact(request, adapter, content_type, inline=False)


@login_required
def version_table(request, version_id):
    from types import SimpleNamespace

    from .spreadsheet import read_xlsx_grid

    version = _version_for(request, version_id)
    name = os.path.basename(version.file.name)
    context = _base_context()
    context["artifact"] = SimpleNamespace(original_name=name)
    context["download_url"] = reverse("dashboard:version_download", args=[version.pk])
    context["back_url"] = reverse("dashboard:document_detail", args=[version.document_id])
    context["grid_sheets"] = read_xlsx_grid(version.file.path)
    return render(request, "dashboard/artifact_table.html", context)

@login_required
def control_detail(request, pk):
    from apps.risks.models import RiskTreatment
    from apps.traceability.services import risk_level

    context = _base_context()
    context.update(control_detail_context(pk))
    # Riesgos cuyo tratamiento eligió este control: sustento de la Declaración de Aplicabilidad.
    treatments = []
    for t in (
        RiskTreatment.objects.filter(control_id=pk)
        .select_related("risk", "responsible")
        .prefetch_related("risk__assessments", "risk__processes")
        .order_by("risk__code")
    ):
        assessments = sorted(t.risk.assessments.all(), key=lambda a: a.assessed_at, reverse=True)
        current = assessments[0] if assessments else None
        treatments.append({
            "treatment": t,
            "risk": t.risk,
            "level": risk_level(current.probability, current.impact) if current else "Pendiente",
            "processes": ", ".join(p.name for p in t.risk.processes.all()) or t.risk.process,
        })
    context["risk_treatments"] = treatments
    return render(request, "dashboard/control_detail.html", context)


@login_required
def user_profile(request, pk):
    from django.core.exceptions import PermissionDenied
    if request.user.pk != pk and not request.user.has_perm("accounts.view_user"):
        raise PermissionDenied
    context = _base_context()
    context.update(
        get_user_profile_context(pk)
    )
    from apps.traceability.selectors import user_links
    person = context["profile_user"]
    context["handovers"] = person.handovers.order_by("-occurred_on", "-created_at") if request.user == person or request.user.has_perm("traceability.view_handover") else []
    context["person_document_links"] = user_links(person) if request.user == person or request.user.has_perm("traceability.view_documentlink") else []
    return render(
        request,
        "dashboard/user_profile.html",
        context,
    )


@login_required
@xframe_options_sameorigin
def artifact_view(request, artifact_id):
    artifact = get_artifact_file(artifact_id)
    if artifact is not None:
        from apps.traceability.access import require_artifact
        require_artifact(request.user, artifact)
    if artifact is None:
        raise Http404("Archivo no encontrado.")
    content_type = artifact.mime_type or mimetypes.guess_type(artifact.original_name)[0] or "application/octet-stream"
    return serve_artifact(request, artifact, content_type, inline=True)


@login_required
def artifact_download(request, artifact_id):
    artifact = get_artifact_file(artifact_id)
    if artifact is not None:
        from apps.traceability.access import require_artifact
        require_artifact(request.user, artifact)
    if artifact is None:
        raise Http404("Archivo no encontrado.")
    handle = artifact.file.open("rb")
    return FileResponse(handle, as_attachment=True, filename=artifact.original_name)


@login_required
def artifact_table(request, artifact_id):
    artifact = get_artifact_file(artifact_id)
    if artifact is not None:
        from apps.traceability.access import require_artifact
        require_artifact(request.user, artifact)
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
    context["grid_sheets"] = read_xlsx_grid(artifact.file.path)
    context["download_url"] = reverse("dashboard:artifact_download", args=[artifact.id])
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
