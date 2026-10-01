from django import forms
from django.forms import inlineformset_factory

from apps.core.etiquetas import traducir_formulario
from apps.processes.models import ProcessNode
from apps.risks.models import Risk

from .models import DocumentLink, Handover, HandoverItem


class StyledForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class RiskForm(StyledForm):
    processes = forms.ModelMultipleChoiceField(
        queryset=ProcessNode.objects.filter(is_active=True), required=False, label="Procesos relacionados"
    )
    probability = forms.IntegerField(min_value=1, max_value=4, required=False, label="Probabilidad (1–4)")
    impact = forms.IntegerField(min_value=1, max_value=5, required=False, label="Consecuencia (1–5)")

    class Meta:
        model = Risk
        fields = (
            "code",
            "identification_type",
            "project_name",
            "origin",
            "category",
            "process",
            "affected_asset_text",
            "affected_assets",
            "scenario",
            "operational_scenario",
            "event",
            "threat",
            "motivation",
            "consequence",
            "existing_controls",
            "finding_origin",
            "evidence_reference",
            "owner",
            "owner_position",
            "status",
            "is_active",
        )
        labels = {
            "process": "Proceso indicado en la fuente",
            "scenario": "Escenario estratégico",
            "threat": "Fuente / amenaza",
            "owner": "Propietario (persona)",
            "owner_position": "Cargo responsable",
            "existing_controls": "Controles existentes",
            "is_active": "Registro activo",
            "origin": "Origen",
            "category": "Categoría",
            "event": "Evento",
            "motivation": "Motivación / DES",
            "consequence": "Consecuencias",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        traducir_formulario(self)
        if not self.instance._state.adding:
            self.initial["processes"] = self.instance.processes.all()
            assessment = self.instance.assessments.first()
            if assessment:
                self.initial.update(probability=assessment.probability, impact=assessment.impact)

    def clean(self):
        data = super().clean()
        if bool(data.get("probability")) != bool(data.get("impact")):
            raise forms.ValidationError(
                "Complete probabilidad y consecuencia juntas, o deje ambas pendientes."
            )
        return data


class LinkForm(StyledForm):
    class Meta:
        model = DocumentLink
        fields = (
            "kind",
            "source_title",
            "source_person",
            "source_position",
            "document",
            "user",
            "position",
            "approved_on",
            "source_date",
            "all_staff",
            "verified",
            "is_active",
        )
        labels = {
            "kind": "Relación",
            "source_title": "Título en la fuente",
            "source_person": "Persona en la fuente",
            "source_position": "Cargo en la fuente",
            "document": "Documento del sistema",
            "user": "Persona vinculada",
            "position": "Cargo vinculado",
            "approved_on": "Fecha validada",
            "source_date": "Fecha original",
            "all_staff": "Todos los colaboradores",
            "verified": "Vínculo revisado y confirmado",
            "is_active": "Vigente",
        }
        widgets = {"approved_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}


class HandoverForm(StyledForm):
    class Meta:
        model = Handover
        fields = ("kind", "occurred_on", "responsible", "notes")
        labels = {
            "kind": "Tipo de acta",
            "occurred_on": "Fecha",
            "responsible": "Responsable de entrega / recepción",
            "notes": "Observaciones",
        }
        widgets = {
            "occurred_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class ItemForm(StyledForm):
    class Meta:
        model = HandoverItem
        fields = (
            "category",
            "description",
            "inventory_code",
            "asset",
            "access",
            "completed",
            "occurred_on",
            "delivered_by",
            "notes",
        )
        labels = {
            "category": "Tipo",
            "description": "Recurso",
            "inventory_code": "Inventario / cuenta",
            "asset": "Activo vinculado",
            "access": "Acceso vinculado",
            "completed": "Entregado / devuelto",
            "occurred_on": "Fecha",
            "delivered_by": "Responsable",
            "notes": "Observaciones",
        }
        widgets = {
            "occurred_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


ItemFormSet = inlineformset_factory(
    Handover,
    HandoverItem,
    form=ItemForm,
    extra=1,
    can_delete=False,
    min_num=1,
    validate_min=True,
    max_num=100,
    validate_max=True,
)


class WorkbookForm(forms.Form):
    kind = forms.ChoiceField(
        label="Contenido",
        choices=[
            ("risks", "Matriz y tratamientos de riesgos"),
            ("owners", "Propietarios documentales"),
            ("access", "Autorizaciones documentales"),
        ],
    )
    file = forms.FileField(label="Excel fuente (.xlsx)")

    def clean_file(self):
        f = self.cleaned_data["file"]
        if not f.name.lower().endswith(".xlsx") or f.size > 15 * 1024 * 1024:
            raise forms.ValidationError("Seleccione un XLSX de hasta 15 MB.")
        return f
