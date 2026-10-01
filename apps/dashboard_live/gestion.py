from django import forms
from django.db import transaction
from django.db.models import Max

from apps.core.etiquetas import traducir_formulario

from .forms import DashboardMetricForm, OesiMetricForm, StrategicFactorForm
from .models import (
    DashboardChange,
    DashboardMetric,
    FactorGroup,
    MatrixType,
    OeeOsiAlignment,
    OesiMetric,
    RequirementOsiAlignment,
    SecurityObjective,
    StakeholderRequirement,
    StrategicFactor,
    StrategicObjective,
)


class _Base(forms.ModelForm):
    def __init__(self, *args, dataset=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.dataset = dataset
        traducir_formulario(self)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_code(self):
        code = (self.cleaned_data.get("code") or "").strip().upper()
        model = self._meta.model
        existe = model.objects.filter(dataset=self.dataset or self.instance.dataset, code__iexact=code).exclude(pk=self.instance.pk)
        if existe.exists():
            raise forms.ValidationError("Ya existe otro elemento con este código en el tablero.")
        return code


class StrategicObjectiveForm(_Base):
    class Meta:
        model = StrategicObjective
        fields = ("code", "description")
        labels = {"code": "Código", "description": "Objetivo estratégico"}
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class SecurityObjectiveForm(_Base):
    class Meta:
        model = SecurityObjective
        fields = ("code", "description")
        labels = {"code": "Código", "description": "Objetivo de seguridad"}
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class StakeholderRequirementForm(_Base):
    class Meta:
        model = StakeholderRequirement
        fields = ("stakeholder", "requirement")
        labels = {"stakeholder": "Parte interesada", "requirement": "Expectativa o requisito"}
        widgets = {"requirement": forms.Textarea(attrs={"rows": 3})}


class NuevoFactorForm(StrategicFactorForm):
    class Meta(StrategicFactorForm.Meta):
        fields = ("matrix_type", "group", "description", "weight", "classification")
        labels = {"matrix_type": "Matriz", "group": "Grupo"}

    def __init__(self, *args, dataset=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["group"].choices = [("", "---------")] + list(FactorGroup.choices)

    def clean(self):
        datos = super().clean()
        validos = {MatrixType.MEFI: {"strength", "weakness"}, MatrixType.MEFE: {"opportunity", "threat"}}
        if datos.get("matrix_type") and datos.get("group") and datos["group"] not in validos.get(datos["matrix_type"], set()):
            self.add_error("group", "En MEFI van fortalezas y debilidades; en MEFE, oportunidades y amenazas.")
        return datos


class _Medicion:
    def __init__(self, *args, dataset=None, **kwargs):
        super().__init__(*args, **kwargs)


class IndicadorForm(_Medicion, DashboardMetricForm):
    pass


class MedicionOesiForm(_Medicion, OesiMetricForm):
    pass


def _siguiente(qs, campo):
    return (qs.aggregate(m=Max(campo))["m"] or 0) + 1


def _codigo_siguiente(qs, prefijo):
    numeros = []
    for code in qs.values_list("code", flat=True):
        resto = code.upper().replace(prefijo, "", 1)
        if code.upper().startswith(prefijo) and resto.isdigit():
            numeros.append(int(resto))
    return f"{prefijo}{(max(numeros) if numeros else 0) + 1}"


TIPOS = {
    "objetivos-estrategicos": {
        "model": StrategicObjective, "form": StrategicObjectiveForm, "titulo": "Objetivos estratégicos (OEE)",
        "singular": "objetivo estratégico", "seccion": "alineacion",
        "codigo": lambda o: o.code, "texto": lambda o: o.description,
        "inicial": lambda ds: {"code": _codigo_siguiente(ds.strategic_objectives.all(), "OEE")},
    },
    "objetivos-seguridad": {
        "model": SecurityObjective, "form": SecurityObjectiveForm, "titulo": "Objetivos de seguridad (OESI)",
        "singular": "objetivo de seguridad", "seccion": "alineacion",
        "codigo": lambda o: o.code, "texto": lambda o: o.description,
        "inicial": lambda ds: {"code": _codigo_siguiente(ds.security_objectives.all(), "OESI")},
    },
    "expectativas": {
        "model": StakeholderRequirement, "form": StakeholderRequirementForm, "titulo": "Expectativas de partes interesadas",
        "singular": "expectativa", "seccion": "alineacion",
        "codigo": lambda o: o.stakeholder, "texto": lambda o: o.requirement,
        "inicial": lambda ds: {},
    },
    "indicadores": {
        "model": DashboardMetric, "form": IndicadorForm, "titulo": "Indicadores del SGSI",
        "singular": "indicador", "seccion": "indicadores",
        "codigo": lambda o: f"M{o.metric_id}", "texto": lambda o: o.description,
        "inicial": lambda ds: {},
    },
    "mediciones-oesi": {
        "model": OesiMetric, "form": MedicionOesiForm, "titulo": "Mediciones de objetivos de seguridad",
        "singular": "medición", "seccion": "objetivos",
        "codigo": lambda o: f"OESI {o.metric_id}", "texto": lambda o: o.description,
        "inicial": lambda ds: {},
    },
    "factores": {
        "model": StrategicFactor, "form": NuevoFactorForm, "titulo": "Factores MEFI y MEFE",
        "singular": "factor", "seccion": "estrategia",
        "codigo": lambda o: f"{o.matrix_type} · {o.get_group_display()}", "texto": lambda o: o.description,
        "inicial": lambda ds: {},
    },
}


def elementos(dataset, tipo):
    model = TIPOS[tipo]["model"]
    return model.objects.filter(dataset=dataset).order_by("-is_active", *model._meta.ordering)


def asegurar_celdas(dataset, actor=None):
    oee = list(dataset.strategic_objectives.filter(is_active=True))
    osi = list(dataset.security_objectives.filter(is_active=True))
    req = list(dataset.stakeholder_requirements.filter(is_active=True))
    existentes = set(dataset.oee_osi_alignments.values_list("strategic_objective_id", "security_objective_id"))
    OeeOsiAlignment.objects.bulk_create([
        OeeOsiAlignment(dataset=dataset, strategic_objective=e, security_objective=s, relation="", source_cell="", created_by=actor, updated_by=actor)
        for e in oee for s in osi if (e.pk, s.pk) not in existentes
    ])
    existentes = set(dataset.requirement_osi_alignments.values_list("requirement_id", "security_objective_id"))
    RequirementOsiAlignment.objects.bulk_create([
        RequirementOsiAlignment(dataset=dataset, requirement=r, security_objective=s, relation="", source_cell="", created_by=actor, updated_by=actor)
        for r in req for s in osi if (r.pk, s.pk) not in existentes
    ])


def _registrar(dataset, tipo, obj, campo, anterior, nuevo, actor):
    DashboardChange.objects.create(
        dataset=dataset, entity_type=tipo, entity_key=str(obj.pk), field_name=campo,
        old_value=str(anterior), new_value=str(nuevo), created_by=actor, updated_by=actor,
    )


@transaction.atomic
def crear(dataset, tipo, form, actor):
    obj = form.save(commit=False)
    obj.dataset = dataset
    obj.created_in_system = True
    obj.created_by = actor
    obj.updated_by = actor
    model = TIPOS[tipo]["model"]
    mismos = model.objects.filter(dataset=dataset)
    if model is SecurityObjective:
        obj.sort_order = _siguiente(mismos, "sort_order")
        obj.source_column = ""
    elif model is StrategicFactor:
        obj.source_row = _siguiente(mismos.filter(matrix_type=obj.matrix_type), "source_row")
    elif model in (DashboardMetric, OesiMetric):
        obj.metric_id = _siguiente(mismos, "metric_id")
        obj.source_row = _siguiente(mismos, "source_row")
    else:
        obj.source_row = _siguiente(mismos, "source_row")
    obj.save()
    form.save_m2m()
    asegurar_celdas(dataset, actor)
    _registrar(dataset, tipo, obj, "alta", "", TIPOS[tipo]["codigo"](obj), actor)
    return obj


@transaction.atomic
def cambiar_vigencia(obj, tipo, vigente, actor):
    if obj.is_active == vigente:
        return obj
    obj.is_active = vigente
    obj.updated_by = actor
    obj.save(update_fields=("is_active", "updated_by", "updated_at"))
    if vigente:
        asegurar_celdas(obj.dataset, actor)
    _registrar(obj.dataset, tipo, obj, "vigencia", "retirado" if vigente else "vigente", "vigente" if vigente else "retirado", actor)
    return obj


def estructura_modificada(dataset):
    for config in TIPOS.values():
        if config["model"].objects.filter(dataset=dataset).filter(is_active=False).exists():
            return True
        if config["model"].objects.filter(dataset=dataset, created_in_system=True).exists():
            return True
    return False
