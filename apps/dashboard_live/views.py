import os
import tempfile
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .change_log import log_changes
from .exporter import export_workbook
from .exporter_sistema import exportar_desde_sistema
from .gestion import TIPOS, cambiar_vigencia, crear, elementos, estructura_modificada
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


def _bullet(value, indicator):
    """Posición del valor actual y de la meta en una barra de 0 a 100 %, y hacia dónde es mejor ir."""
    from decimal import Decimal

    from .logic import parse_indicator

    operator, target = parse_indicator(indicator)
    if value is None or target is None:
        return None
    value, target = Decimal(value), Decimal(target)
    percent_scale = "%" in (indicator or "") and value <= 100 and target <= 100
    top = Decimal("100") if percent_scale else max(value, target, Decimal("1")) * Decimal("1.25")
    return {
        "value_pct": float(min(Decimal("100"), max(Decimal("0"), value / top * 100))),
        "target_pct": float(min(Decimal("100"), max(Decimal("0"), target / top * 100))),
        "direction": "up" if operator in (">=", ">") else "down" if operator in ("<=", "<") else "eq",
        "unit": "%" if "%" in (indicator or "") else "",
    }


@login_required
def home(request):
    """Solo el armazón con esqueletos: los datos llegan por la API JSON (carga asíncrona)."""
    from .selectors import current_dataset

    dataset = current_dataset()
    return render(request, "dashboard_live/home.html", {
        "dataset": dataset,
        "can_change": _can_change(request),
    })


def _num(value):
    return None if value is None else float(value)


def dashboard_payload(request, refresh=False):
    from django.urls import reverse

    from .overview import system_overview

    ctx = build_dashboard_context()
    can_change = _can_change(request)
    payload = {
        "can_change": can_change,
        "overview": system_overview(refresh=refresh),
        "links": {
            "gestionar": {clave: reverse("dashboard_live:gestionar", args=[clave]) for clave in TIPOS} if can_change else {},
            "risks": reverse("traceability:risks"),
            "incidents": reverse("registers:detail", args=["registro-incidentes"]),
            "corrective": reverse("registers:detail", args=["medidas-correctivas"]),
            "assets": reverse("assets:list"),
            "annex": reverse("dashboard:annex_controls"),
            "clause": reverse("dashboard:clause_detail", args=["0"]).replace("/0/", "/{c}/"),
        },
        "dataset": None,
    }
    dataset = ctx.get("dataset")
    if not dataset:
        return payload

    def metric(row, oesi=False):
        obj = row["obj"]
        value = row.get("effective", obj.current_value) if not oesi else obj.current_value
        return {
            "id": obj.metric_id, "description": obj.description, "pdca": getattr(obj, "pdca_cycle", ""),
            "display": row["display"], "value": _num(value), "indicator": obj.indicator,
            "ok": row["compliance"] == "SI", "bullet": _bullet(value, obj.indicator),
            "responsible": obj.responsible_text, "period": obj.period,
            "plan": getattr(obj, "action_plan", ""), "edit_url": row["edit_url"] if can_change else "",
        }

    security = ctx["security"]
    index = {obj.pk: i for i, obj in enumerate(security)}

    def matrix(objects, alignments, attr, name):
        cells = {}
        for a in alignments:
            row = cells.setdefault(getattr(a, f"{attr}_id"), [None] * len(security))
            row[index[a.security_objective_id]] = {
                "rel": a.relation,
                "url": reverse(f"dashboard_live:toggle_{name}_alignment", args=[a.pk]) if can_change else "",
            }
        return [{"obj": obj, "cells": cells.get(obj.pk, [None] * len(security))} for obj in objects]

    labels = {"strength": ("Fortalezas", "ok"), "weakness": ("Debilidades", "bad"),
              "opportunity": ("Oportunidades", "info"), "threat": ("Amenazas", "warn")}
    groups = []
    for summary in (ctx["mefi"], ctx["mefe"]):
        for group, score in summary["groups"].items():
            label, tone = labels.get(str(group), (str(group), "calm"))
            groups.append({"label": label, "tone": tone, "value": _num(score),
                           "count": sum(1 for f in summary["rows"] if f.group == group)})

    payload.update({
        "dataset": {"name": dataset.original_name, "version": dataset.version_label,
                    "updated": dataset.updated_at.isoformat() if dataset.updated_at else ""},
        "summary": {
            "sgsi": [ctx["sgsi_yes"], ctx["sgsi_total"]], "oesi": [ctx["oesi_yes"], ctx["oesi_total"]],
            "oee": [ctx["oee_obtained"], ctx["oee_expected"]], "req": [ctx["req_obtained"], ctx["req_expected"]],
        },
        "sgsi": [metric(r) for r in ctx["sgsi_rows"]],
        "oesi": [metric(r, oesi=True) for r in ctx["oesi_rows"]],
        "security": [{"code": s.code, "description": s.description} for s in security],
        "oee_matrix": [{"code": r["obj"].code, "text": r["obj"].description, "cells": r["cells"]}
                       for r in matrix(ctx["strategic"], ctx["oee_alignments"], "strategic_objective", "oee")],
        "req_matrix": [{"code": r["obj"].stakeholder, "text": r["obj"].requirement, "cells": r["cells"]}
                       for r in matrix(ctx["requirements"], ctx["req_alignments"], "requirement", "req")],
        "osi_scores": [{"code": s.code, "description": s.description, "oee": ctx["oee_scores"][s.code],
                        "req": ctx["req_scores"][s.code]} for s in security],
        "factors": groups,
        "efi": _num(ctx["efi"]), "efe": _num(ctx["efe"]), "averaged": ctx.get("averaged", False),
        "warnings": ctx["warnings"],
    })
    return payload


@login_required
def dashboard_data(request):
    """API del tablero. Devuelve una «versión» (huella del contenido): si el cliente ya la tiene,
    responde solo {"unchanged": true} y el navegador no vuelve a dibujar nada."""
    import hashlib
    import json

    from django.core.serializers.json import DjangoJSONEncoder

    payload = dashboard_payload(request, refresh=request.GET.get("refresh") == "1")
    body = json.dumps(payload, cls=DjangoJSONEncoder, ensure_ascii=False, sort_keys=True)
    version = hashlib.sha1(body.encode()).hexdigest()[:12]
    if request.GET.get("v") == version:
        return JsonResponse({"unchanged": True, "version": version})
    payload["version"] = version
    payload["server_time"] = timezone.now().isoformat()
    return JsonResponse(payload, encoder=DjangoJSONEncoder, json_dumps_params={"ensure_ascii": False})


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


def _requested_relation(request, current):
    if "relation" not in request.POST:
        return _next_relation(current)
    value = request.POST["relation"].strip().upper()
    if value not in ("P", "S", ""):
        return None
    return value


def _cell(name, alignment, previous):
    return {
        "url": reverse(f"dashboard_live:toggle_{name}_alignment", args=[alignment.pk]),
        "relation": alignment.relation,
        "previous": previous,
    }


@login_required
@require_POST
def toggle_oee_alignment(request, pk):
    if not _can_change(request):
        raise PermissionDenied
    alignment = get_object_or_404(OeeOsiAlignment, pk=pk, dataset__is_current=True)
    old = alignment.relation
    new = _requested_relation(request, old)
    if new is None:
        return JsonResponse({"ok": False, "error": "Relación no válida."}, status=400)
    changed = []
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
            changed.append(_cell("oee", sibling, sibling_old))
    if new != old:
        alignment.relation = new
        alignment.updated_by = request.user
        alignment.save(update_fields=("relation", "updated_by", "updated_at"))
        _record_alignment_change(request, alignment, "oee_osi", old, new)
    changed.insert(0, _cell("oee", alignment, old))
    return JsonResponse({"ok": True, "relation": new, "changed": changed})


@login_required
@require_POST
def toggle_req_alignment(request, pk):
    if not _can_change(request):
        raise PermissionDenied
    alignment = get_object_or_404(RequirementOsiAlignment, pk=pk, dataset__is_current=True)
    old = alignment.relation
    new = _requested_relation(request, old)
    if new is None:
        return JsonResponse({"ok": False, "error": "Relación no válida."}, status=400)
    if new != old:
        alignment.relation = new
        alignment.updated_by = request.user
        alignment.save(update_fields=("relation", "updated_by", "updated_at"))
        _record_alignment_change(request, alignment, "req_osi", old, new)
    return JsonResponse({"ok": True, "relation": new, "changed": [_cell("req", alignment, old)]})


@login_required
def download_updated_workbook(request):
    dataset = current_dataset()
    if dataset is None:
        messages.error(request, "No existe un Dashboard vigente.")
        return redirect("/")

    content = exportar_desde_sistema() if estructura_modificada(dataset) else export_workbook(dataset)
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


def _tipo(tipo):
    if tipo not in TIPOS:
        raise Http404("Tipo no válido.")
    return TIPOS[tipo]


def _permiso(request, model, accion):
    return request.user.is_superuser or request.user.has_perm(f"{model._meta.app_label}.{accion}_{model._meta.model_name}")


def _volver(tipo):
    return f"{reverse('dashboard_live:gestionar', args=[tipo])}"


@login_required
def gestionar(request, tipo):
    config = _tipo(tipo)
    dataset = current_dataset()
    if dataset is None:
        messages.error(request, "Primero suba el tablero del SGSI.")
        return redirect("/")
    if not _permiso(request, config["model"], "view") and not _can_change(request):
        raise PermissionDenied
    filas = [{
        "obj": obj,
        "codigo": config["codigo"](obj),
        "texto": config["texto"](obj),
        "editar": reverse("dashboard_live:editar_elemento", args=[tipo, obj.pk]),
        "vigencia": reverse("dashboard_live:vigencia_elemento", args=[tipo, obj.pk]),
    } for obj in elementos(dataset, tipo)]
    return render(request, "dashboard_live/gestionar.html", {
        "tipos": [{"clave": k, "titulo": v["titulo"], "activo": k == tipo} for k, v in TIPOS.items()],
        "tipo": tipo,
        "config": config,
        "filas": filas,
        "vigentes": sum(1 for f in filas if f["obj"].is_active),
        "puede_crear": _permiso(request, config["model"], "add"),
        "puede_cambiar": _permiso(request, config["model"], "change"),
        "volver_tablero": f"{reverse('dashboard_live:home')}#{config['seccion']}",
        "excel_del_sistema": estructura_modificada(dataset),
    })


def _formulario(request, tipo, obj=None):
    config = _tipo(tipo)
    dataset = current_dataset()
    if dataset is None:
        raise Http404("No hay tablero vigente.")
    accion = "change" if obj else "add"
    if not _permiso(request, config["model"], accion):
        raise PermissionDenied
    form_class = config["form"]
    if request.method == "POST":
        form = form_class(request.POST, instance=obj, dataset=dataset)
        if form.is_valid():
            if obj is None:
                creado = crear(dataset, tipo, form, request.user)
                messages.success(request, f"Se agregó {config['singular']} {config['codigo'](creado)}.")
            else:
                antes = {campo: getattr(obj, campo) for campo in form_class.Meta.fields}
                guardado = form.save(commit=False)
                guardado.updated_by = request.user
                guardado.save()
                log_changes(dataset=dataset, entity_type=tipo, entity_key=str(obj.pk), before=antes,
                            after={campo: getattr(guardado, campo) for campo in form_class.Meta.fields},
                            actor=request.user, trace_lookup=_trace_lookup(dataset, tipo, str(obj.pk)))
                messages.success(request, "Cambios guardados.")
            return redirect(_volver(tipo))
    else:
        form = form_class(instance=obj, dataset=dataset, initial=None if obj else config["inicial"](dataset))
    titulo = f"Editar {config['singular']} {config['codigo'](obj)}" if obj else f"Nuevo {config['singular']}"
    return render(request, "dashboard_live/edit_form.html", {
        "title": titulo,
        "subtitle": config["titulo"],
        "form": form,
        "return_url": _volver(tipo),
        "trace": [],
    })


@login_required
def crear_elemento(request, tipo):
    return _formulario(request, tipo)


@login_required
def editar_elemento(request, tipo, pk):
    config = _tipo(tipo)
    obj = get_object_or_404(config["model"], pk=pk, dataset__is_current=True)
    return _formulario(request, tipo, obj)


@login_required
@require_POST
def vigencia_elemento(request, tipo, pk):
    config = _tipo(tipo)
    obj = get_object_or_404(config["model"], pk=pk, dataset__is_current=True)
    if not _permiso(request, config["model"], "change"):
        raise PermissionDenied
    vigente = request.POST.get("vigente") == "1"
    cambiar_vigencia(obj, tipo, vigente, request.user)
    messages.success(request, f"{config['codigo'](obj)} {'vuelve a estar vigente' if vigente else 'quedó retirado; su historial se conserva'}.")
    return redirect(_volver(tipo))
