
from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.forms import modelform_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.accounts.models import (
    AccessReview,
    CorporateSystem,
    SystemAccess,
)
from apps.assets.models import (
    Asset,
    AssetMovement,
    Maintenance,
)
from apps.assurance.models import (
    Audit,
    Finding,
    ImprovementAction,
)
from apps.controls.models import (
    Control,
    ControlEvidence,
)
from apps.controls.models_iso import (
    ISOClause,
    ISORequirement,
)
from apps.dashboard.models import (
    ObjectiveAlignment,
    SGSIMetric,
    SecurityObjective,
    StrategicFactor,
)
from apps.documents.models import (
    Document,
    Evidence,
)
from apps.incidents.models import (
    Incident,
    IncidentEvent,
    Vulnerability,
)
from apps.risks.models import (
    Risk,
    RiskAssessment,
    RiskTreatment,
)
from apps.core.etiquetas import etiqueta_campo, etiqueta_modelo, traducir_formulario
from .product_contexts import organization_board_context


User = get_user_model()

ENTITY_REGISTRY = {
    "usuarios": {"model": User, "title": "Colaboradores", "icon": "i-users", "group": "Identidades y accesos"},
    "sistemas": {"model": CorporateSystem, "title": "Sistemas corporativos", "icon": "i-monitor", "group": "Identidades y accesos"},
    "accesos": {"model": SystemAccess, "title": "Accesos a sistemas", "icon": "i-key", "group": "Identidades y accesos"},
    "revisiones-acceso": {"model": AccessReview, "title": "Revisiones de acceso", "icon": "i-file-check", "group": "Identidades y accesos"},
    "activos": {"model": Asset, "title": "Activos y equipos", "icon": "i-assets", "group": "Activos y equipos"},
    "movimientos-activo": {"model": AssetMovement, "title": "Movimientos de activos", "icon": "i-process", "group": "Activos y equipos"},
    "mantenimientos": {"model": Maintenance, "title": "Mantenimientos", "icon": "i-controls", "group": "Activos y equipos"},
    "riesgos": {"model": Risk, "title": "Riesgos", "icon": "i-risk", "group": "Riesgos"},
    "evaluaciones-riesgo": {"model": RiskAssessment, "title": "Evaluaciones de riesgo", "icon": "i-risk", "group": "Riesgos"},
    "tratamientos-riesgo": {"model": RiskTreatment, "title": "Tratamientos de riesgo", "icon": "i-file-check", "group": "Riesgos"},
    "incidentes": {"model": Incident, "title": "Incidentes", "icon": "i-incident", "group": "Incidentes y vulnerabilidades"},
    "eventos-incidente": {"model": IncidentEvent, "title": "Eventos de incidente", "icon": "i-incident", "group": "Incidentes y vulnerabilidades"},
    "vulnerabilidades": {"model": Vulnerability, "title": "Vulnerabilidades", "icon": "i-vuln", "group": "Incidentes y vulnerabilidades"},
    "documentos": {"model": Document, "title": "Documentos", "icon": "i-docs", "group": "Documentos y evidencias"},
    "evidencias": {"model": Evidence, "title": "Evidencias", "icon": "i-file-check", "group": "Documentos y evidencias"},
    "controles": {"model": Control, "title": "Controles ISO 27001", "icon": "i-controls", "group": "Anexo A"},
    "evidencia-control": {"model": ControlEvidence, "title": "Evidencias por control", "icon": "i-file-check", "group": "Anexo A"},
    "requisitos-iso": {"model": ISORequirement, "title": "Requisitos ISO / Sustentos", "icon": "i-book", "group": "Norma ISO"},
    "clausulas-iso": {"model": ISOClause, "title": "Cláusulas ISO", "icon": "i-book", "group": "Norma ISO"},
    "auditorias": {"model": Audit, "title": "Auditorías", "icon": "i-audit", "group": "Auditoría y mejora"},
    "hallazgos": {"model": Finding, "title": "Hallazgos", "icon": "i-file-missing", "group": "Auditoría y mejora"},
    "acciones-mejora": {"model": ImprovementAction, "title": "Acciones de mejora", "icon": "i-file-check", "group": "Auditoría y mejora"},
    "metricas-sgsi": {"model": SGSIMetric, "title": "Métricas SGSI", "icon": "i-reports", "group": "Reportes y métricas"},
    "objetivos-oesi": {"model": SecurityObjective, "title": "Objetivos OESI", "icon": "i-reports", "group": "Reportes y métricas"},
    "alineamientos": {"model": ObjectiveAlignment, "title": "Alineamientos estratégicos", "icon": "i-reports", "group": "Reportes y métricas"},
    "factores-estrategicos": {"model": StrategicFactor, "title": "MEFI / MEFE", "icon": "i-reports", "group": "Reportes y métricas"},
}

MODEL_TO_ENTITY = {cfg["model"]._meta.label_lower: key for key, cfg in ENTITY_REGISTRY.items()}

FIELD_PRIORITY = [
    "business_code", "code", "username", "name", "title", "description",
    "area", "position", "category", "type", "asset_type", "status", "state",
    "owner", "user", "assigned_to", "responsible", "severity", "risk_level",
    "version", "updated_at",
]

EXCLUDED_FORM_FIELDS = {
    "id", "created_at", "updated_at", "created_by", "updated_by", "password",
    "last_login", "date_joined", "is_superuser", "user_permissions", "groups",
}

def get_entity_config(entity):
    cfg = ENTITY_REGISTRY.get(entity)
    if cfg is None:
        raise KeyError(entity)
    return cfg

def get_group_links(entity):
    current = get_entity_config(entity)
    return [
        {"entity": key, "title": cfg["title"], "icon": cfg["icon"], "active": key == entity}
        for key, cfg in ENTITY_REGISTRY.items()
        if cfg["group"] == current["group"]
    ]

def _perm_name(model, action):
    return f"{model._meta.app_label}.{action}_{model._meta.model_name}"

def ensure_permission(request, model, action):
    if request.user.is_superuser:
        return
    if not request.user.has_perm(_perm_name(model, action)):
        raise PermissionDenied

def _field_exists(model, name):
    try:
        model._meta.get_field(name)
        return True
    except Exception:
        return False

def _list_columns(model):
    available = [name for name in FIELD_PRIORITY if _field_exists(model, name)]
    if len(available) >= 6:
        return available[:7]
    for field in model._meta.get_fields():
        if len(available) >= 7:
            break
        if field.auto_created or field.many_to_many or field.one_to_many or field.name in available or field.name in {"id", "created_by", "updated_by"}:
            continue
        available.append(field.name)
    return available

def _search_fields(model):
    fields = []
    for field in model._meta.get_fields():
        if field.auto_created or field.is_relation:
            continue
        if field.get_internal_type() in {"CharField", "TextField", "EmailField"}:
            fields.append(field.name)
    return fields[:12]

def _object_label(obj):
    for name in ("business_code", "code", "username", "name", "title", "description"):
        if hasattr(obj, name):
            value = getattr(obj, name, "")
            if value:
                return str(value)
    return str(obj)

def object_url_by_entity(entity_key, obj):
    if entity_key == "documentos":
        return reverse("dashboard:document_detail", kwargs={"document_id": obj.pk})
    if entity_key == "controles":
        return reverse("dashboard:control_detail", kwargs={"pk": obj.pk})
    if entity_key == "usuarios":
        return reverse("dashboard:user_profile", kwargs={"pk": obj.pk})
    return reverse("dashboard:entity_detail", kwargs={"entity": entity_key, "pk": obj.pk})

def object_url_for_model(obj):
    key = MODEL_TO_ENTITY.get(obj.__class__._meta.label_lower)
    if not key:
        return ""
    return object_url_by_entity(key, obj)

def _display_value(obj, field):
    if field.many_to_many:
        manager = getattr(obj, field.name)
        values = list(manager.all()[:4])
        text = ", ".join(str(item) for item in values)
        if manager.count() > 4:
            text += "…"
        return text or "—", ""

    value = getattr(obj, field.name, None)
    if field.is_relation:
        if value is None:
            return "—", ""
        return str(value), object_url_for_model(value)

    display_method = getattr(obj, f"get_{field.name}_display", None)
    if callable(display_method):
        try:
            return str(display_method()), ""
        except Exception:
            pass

    if value in (None, ""):
        return "—", ""
    if isinstance(value, bool):
        return ("Sí" if value else "No"), ""
    return str(value), ""

def _editable_fields(model):
    fields = []
    for field in model._meta.get_fields():
        if field.auto_created or not getattr(field, "editable", False) or field.name in EXCLUDED_FORM_FIELDS:
            continue
        fields.append(field.name)
    if model is User:
        fields = [name for name in fields if name not in {"is_staff"}]
    return fields

def _build_form(model):
    fields = _editable_fields(model)
    class StyledForm(modelform_factory(model, fields=fields)):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            traducir_formulario(self)
            for name, field in self.fields.items():
                field.widget.attrs.setdefault("class", "form-control")
                if getattr(field.widget, "input_type", "") == "checkbox":
                    field.widget.attrs.pop("class", None)
    return StyledForm

def _field_cards(obj):
    output = []
    for field in obj._meta.get_fields():
        if field.auto_created or field.one_to_many or (field.one_to_one and not getattr(field, "concrete", False)):
            continue
        if field.name in {"password"}:
            continue
        try:
            value, url = _display_value(obj, field)
        except Exception:
            continue
        output.append({"label": etiqueta_campo(field), "value": value, "url": url})
    return output

def _reverse_relations(obj):
    blocks = []
    for rel in obj._meta.related_objects:
        accessor = rel.get_accessor_name()
        if not accessor:
            continue
        try:
            manager = getattr(obj, accessor)
            queryset = manager.all()
            count = queryset.count()
            items = list(queryset[:20])
        except Exception:
            continue
        if not items:
            continue
        rows = [{"label": _object_label(item), "url": object_url_for_model(item)} for item in items]
        blocks.append({"title": etiqueta_modelo(rel.related_model, plural=True), "count": count, "rows": rows})
    return blocks

def entity_list_context(request, entity):
    cfg = get_entity_config(entity)
    model = cfg["model"]
    ensure_permission(request, model, "view")
    queryset = model.objects.all()
    search = request.GET.get("q", "").strip()
    if search:
        query = Q()
        for field_name in _search_fields(model):
            query |= Q(**{f"{field_name}__icontains": search})
        queryset = queryset.filter(query)
    try:
        queryset = queryset.order_by("-updated_at")
    except Exception:
        pass
    queryset = queryset[:250]
    columns = _list_columns(model)
    fields = [model._meta.get_field(name) for name in columns]
    rows = []
    for obj in queryset:
        cells = []
        for field in fields:
            value, url = _display_value(obj, field)
            cells.append({"value": value, "url": url})
        rows.append({"obj": obj, "label": _object_label(obj), "url": object_url_by_entity(entity, obj), "cells": cells})
    return {
        "entity_key": entity,
        "entity": cfg,
        "columns": [{"name": field.name, "label": etiqueta_campo(field)} for field in fields],
        "rows": rows,
        "search": search,
        "group_links": get_group_links(entity),
        "can_add": request.user.is_superuser or request.user.has_perm(_perm_name(model, "add")),
    }

def entity_list_view(request, entity):
    return render(request, "dashboard/entity_list.html", entity_list_context(request, entity))

def entity_detail_view(request, entity, pk):
    cfg = get_entity_config(entity)
    model = cfg["model"]
    ensure_permission(request, model, "view")
    obj = get_object_or_404(model, pk=pk)
    return render(request, "dashboard/entity_detail.html", {
        "entity_key": entity,
        "entity": cfg,
        "object": obj,
        "object_label": _object_label(obj),
        "fields": _field_cards(obj),
        "relations": _reverse_relations(obj),
        "group_links": get_group_links(entity),
        "can_change": request.user.is_superuser or request.user.has_perm(_perm_name(model, "change")),
    })

def entity_form_view(request, entity, pk=None):
    cfg = get_entity_config(entity)
    model = cfg["model"]
    action = "change" if pk is not None else "add"
    ensure_permission(request, model, action)
    obj = get_object_or_404(model, pk=pk) if pk is not None else None
    Form = _build_form(model)
    if request.method == "POST":
        form = Form(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            instance = form.save(commit=False)
            if hasattr(instance, "updated_by_id"):
                instance.updated_by = request.user
            if obj is None and hasattr(instance, "created_by_id"):
                instance.created_by = request.user
            instance.save()
            form.save_m2m()
            messages.success(request, "Cambios guardados correctamente.")
            return redirect(object_url_by_entity(entity, instance))
    else:
        if obj is None:
            initial = {}
            for field_name in _editable_fields(model):
                if request.GET.get(field_name):
                    initial[field_name] = request.GET.get(field_name)
            form = Form(initial=initial)
        else:
            form = Form(instance=obj)
    return render(request, "dashboard/entity_form.html", {
        "entity_key": entity,
        "entity": cfg,
        "object": obj,
        "form": form,
        "group_links": get_group_links(entity),
    })

def organization_context():
    users = list(User.objects.order_by("last_name", "first_name", "username"))
    board = organization_board_context(users)
    board["user_count"] = len(users)
    return board
