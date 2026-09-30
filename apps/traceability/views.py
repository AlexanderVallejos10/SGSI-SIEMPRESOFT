from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.organization.models import OrganizationalArea
from apps.processes.models import ProcessNode
from apps.risks.models import IdentificationType, Risk, RiskAssessment

from .forms import HandoverForm, LinkForm, RiskForm, WorkbookForm
from .importer import import_workbook
from .models import DocumentLink, Handover, SourceRow
from .selectors import risk_rows
from .services import issue_handover, render_docx


def permitted(permission):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not request.user.has_perm(permission):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapped

    return decorator


@permitted("risks.view_risk")
def risks(request):
    qs = Risk.objects.filter(is_active=True)
    process = None
    if request.GET.get("process"):
        process = get_object_or_404(ProcessNode, pk=request.GET["process"])
        qs = qs.filter(processes=process)
    if request.GET.get("area"):
        area = get_object_or_404(OrganizationalArea, pk=request.GET["area"])
        qs = qs.filter(
            Q(processes__primary_area=area)
            | Q(processes__involved_areas=area)
            | Q(processes__owner_position__area=area)
            | Q(owner_position__area=area)
        )
    if request.GET.get("pending"):
        qs = qs.filter(processes__isnull=True)
    selected_type = request.GET.get("tipo", "")
    if selected_type in IdentificationType.values:
        qs = qs.filter(identification_type=selected_type)
    rows = risk_rows(qs.distinct().order_by("code"))
    return render(
        request,
        "traceability/risks.html",
        {
            "rows": rows,
            "process": process,
            "processes": ProcessNode.objects.filter(is_active=True),
            "areas": OrganizationalArea.objects.filter(is_active=True),
            "can_change": request.user.has_perm("risks.change_risk"),
            "can_add": request.user.has_perm("risks.add_risk"),
            "selected_area": request.GET.get("area", ""),
            "pending": bool(request.GET.get("pending")),
            "id_types": IdentificationType.choices,
            "selected_type": selected_type,
        },
    )


@login_required
@transaction.atomic
def risk_edit(request, pk=None):
    if not request.user.has_perm("risks.change_risk" if pk else "risks.add_risk"):
        raise PermissionDenied
    obj = get_object_or_404(Risk, pk=pk) if pk else None
    form = RiskForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        risk = form.save(commit=False)
        risk.updated_by = request.user
        if not obj:
            risk.created_by = request.user
        risk.save()
        form.save_m2m()
        risk.processes.set(form.cleaned_data["processes"])
        p, i = form.cleaned_data["probability"], form.cleaned_data["impact"]
        current = risk.assessments.first()
        if p and i and (not current or (current.probability, current.impact) != (p, i)):
            RiskAssessment.objects.create(
                risk=risk,
                assessed_at=timezone.now(),
                probability=p,
                impact=i,
                inherent_score=p * i,
                created_by=request.user,
                updated_by=request.user,
            )
        messages.success(request, "Riesgo guardado. Las evaluaciones anteriores se conservan.")
        return redirect("traceability:risks")
    return render(
        request, "traceability/form.html", {"form": form, "title": "Editar riesgo" if obj else "Nuevo riesgo"}
    )


@permitted("traceability.view_documentlink")
def links(request):
    qs = DocumentLink.objects.select_related("user", "position", "document").order_by("source_title")
    if request.GET.get("pending"):
        qs = qs.filter(verified=False)
    return render(
        request,
        "traceability/links.html",
        {"links": qs, "can_change": request.user.has_perm("traceability.change_documentlink")},
    )


@login_required
@transaction.atomic
def link_edit(request, pk=None):
    if not request.user.has_perm(
        "traceability.change_documentlink" if pk else "traceability.add_documentlink"
    ):
        raise PermissionDenied
    obj = get_object_or_404(DocumentLink, pk=pk) if pk else None
    form = LinkForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        link = form.save(commit=False)
        link.updated_by = request.user
        if not obj:
            link.created_by = request.user
        link.save()
        if link.kind == "owner" and link.verified and link.is_active:
            # One current owner; keep prior assignments as history.
            for old in DocumentLink.objects.filter(
                document=link.document, kind="owner", verified=True, is_active=True
            ).exclude(pk=link.pk):
                old.is_active = False
                old.updated_by = request.user
                old.save()
            link.document.owner = link.user
            link.document.updated_by = request.user
            link.document.save()
        messages.success(request, "Relación documental guardada.")
        return redirect("traceability:links")
    return render(request, "traceability/form.html", {"form": form, "title": "Relación documental"})


@permitted("traceability.add_importbatch")
def workbook_upload(request):
    # Import affects risks and grants; keep all required write permissions explicit.
    form = WorkbookForm(request.POST or None, request.FILES or None)
    result = None
    if request.method == "POST" and form.is_valid():
        kind = form.cleaned_data["kind"]
        required = (
            ("risks.add_risk", "risks.add_riskassessment", "risks.add_risktreatment")
            if kind == "risks"
            else ("traceability.add_documentlink",)
        )
        if not request.user.has_perms(required):
            raise PermissionDenied
        try:
            result = import_workbook(
                form.cleaned_data["file"], kind, request.user, apply=request.POST.get("action") == "apply"
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            if request.POST.get("action") == "apply":
                messages.success(request, "Carga procesada. Revise las vinculaciones pendientes.")
    return render(request, "traceability/import.html", {"form": form, "result": result})


@permitted("traceability.view_sourcerow")
def source_rows(request):
    qs = (
        SourceRow.objects.exclude(issue="")
        .select_related("batch", "risk")
        .order_by("batch__name", "sheet", "row_number")
    )
    from django.core.paginator import Paginator

    page = Paginator(qs, 50).get_page(request.GET.get("page"))
    return render(request, "traceability/sources.html", {"page": page})


@login_required
@transaction.atomic
def handover_edit(request, user_id=None, pk=None):
    if not request.user.has_perm("traceability.change_handover" if pk else "traceability.add_handover"):
        raise PermissionDenied
    obj = (
        get_object_or_404(Handover.objects.select_for_update(), pk=pk)
        if pk
        else Handover(user=get_object_or_404(get_user_model(), pk=user_id))
    )
    if obj.status != "draft":
        raise PermissionDenied("Las actas emitidas conservan su contenido.")
    initial = {
        "occurred_on": timezone.localdate(),
        "responsible": request.user,
        "kind": request.GET.get("kind", "entry"),
    }
    form = HandoverForm(request.POST or None, instance=obj, initial=initial)
    initial_items = []
    if not pk and request.method == "GET":
        from apps.assets.models import Asset

        for asset in Asset.objects.filter(custodian=obj.user):
            initial_items.append(
                {
                    "category": "material",
                    "description": asset.name,
                    "inventory_code": asset.code,
                    "asset": asset.pk,
                }
            )
        for access in obj.user.system_accesses.filter(status="active").select_related("system"):
            initial_items.append(
                {
                    "category": "access",
                    "description": str(access.system),
                    "inventory_code": access.business_code,
                    "access": access.pk,
                }
            )
        if not initial_items:
            initial_items = [{"category": "material", "description": ""}]
    from django.forms import inlineformset_factory

    from .forms import ItemForm
    from .models import HandoverItem

    Factory = inlineformset_factory(
        Handover,
        HandoverItem,
        form=ItemForm,
        extra=max(1, len(initial_items)),
        can_delete=False,
        min_num=0,
        max_num=100,
        validate_max=True,
    )
    formset = Factory(request.POST or None, instance=obj, initial=initial_items, prefix="items")
    for item_form in formset:
        item_form.fields["access"].queryset = obj.user.system_accesses.all()
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        if not any(f.cleaned_data and f.cleaned_data.get("description") for f in formset):
            form.add_error(None, "Agregue al menos un recurso.")
        else:
            obj = form.save(commit=False)
            obj.updated_by = request.user
            if not pk:
                obj.created_by = request.user
            obj.save()
            formset.instance = obj
            for item in formset.save(commit=False):
                item.updated_by = request.user
                if item._state.adding:
                    item.created_by = request.user
                item.full_clean()
                item.save()
            return redirect("traceability:handover_detail", pk=obj.pk)
    return render(
        request, "traceability/handover_form.html", {"form": form, "formset": formset, "person": obj.user}
    )


@login_required
def handover_detail(request, pk):
    act = get_object_or_404(Handover.objects.select_related("user", "responsible"), pk=pk)
    if request.user != act.user and not request.user.has_perm("traceability.view_handover"):
        raise PermissionDenied
    return render(
        request,
        "traceability/handover.html",
        {
            "act": act,
            "items": act.snapshot.get("items", []) if act.status != "draft" else act.items.all(),
            "can_change": request.user.has_perm("traceability.change_handover"),
        },
    )


@permitted("traceability.change_handover")
@require_POST
def handover_issue(request, pk):
    act = get_object_or_404(Handover, pk=pk)
    try:
        issue_handover(act, request.user)
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("traceability:handover_detail", pk=pk)


@login_required
def handover_download(request, pk):
    act = get_object_or_404(Handover, pk=pk)
    if request.user != act.user and not request.user.has_perm("traceability.view_handover"):
        raise PermissionDenied
    if act.status == "draft":
        raise PermissionDenied("Emita el acta antes de descargarla.")
    return FileResponse(render_docx(act), as_attachment=True, filename=f"ACT-{str(act.pk)[:8]}.docx")


@permitted("traceability.change_handover")
@require_POST
@transaction.atomic
def handover_signed(request, pk):
    act = get_object_or_404(Handover.objects.select_for_update(), pk=pk)
    f = request.FILES.get("signed_file")
    if (
        act.status != "issued"
        or not f
        or f.size > 15 * 1024 * 1024
        or not f.name.lower().endswith(".pdf")
        or not f.read(5).startswith(b"%PDF")
    ):
        messages.error(request, "Adjunte un PDF de hasta 15 MB a un acta emitida sin firma adjunta.")
    else:
        f.seek(0)
        act.signed_file = f
        act.status = "signed"
        act.updated_by = request.user
        act.save()
    return redirect("traceability:handover_detail", pk=pk)


@login_required
def signed_download(request, pk):
    act = get_object_or_404(Handover, pk=pk, status="signed")
    if request.user != act.user and not request.user.has_perm("traceability.view_handover"):
        raise PermissionDenied
    return FileResponse(
        act.signed_file.open("rb"), as_attachment=True, filename=f"ACT-{str(act.pk)[:8]}-firmada.pdf"
    )


@permitted("risks.change_risk")
@require_POST
@transaction.atomic
def risk_link_many(request):
    process = get_object_or_404(ProcessNode, pk=request.POST.get("process"), is_active=True)
    ids = request.POST.getlist("risks")
    if len(ids) > 500:
        raise ValidationError("Seleccione hasta 500 riesgos por operación.")
    risks = list(Risk.objects.filter(pk__in=ids, is_active=True))
    for risk in risks:
        risk.processes.add(process)
        risk.updated_by = request.user
        risk.save(update_fields=["updated_by", "updated_at"])
    messages.success(
        request, f"{len(risks)} riesgos vinculados a {process.name}. Se conservaron sus otros procesos."
    )
    return redirect(reverse("traceability:risks") + f"?process={process.pk}")


@permitted("risks.view_risk")
def risks_export(request):
    """Matriz de riesgos en el formato de la plantilla del Oficial de Seguridad (se puede volver a importar)."""
    from apps.core.exports import excel_download

    from .exporter import build_risk_matrix

    return excel_download(request, build_risk_matrix(), "Matriz_de_riesgos_SiempreSoft", module="risks", entity="Risk")

