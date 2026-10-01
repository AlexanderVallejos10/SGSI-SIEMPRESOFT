from pathlib import Path

from django import forms

from apps.core.etiquetas import traducir_formulario

from .models import DashboardMetric, OesiMetric, StrategicFactor


class DashboardMetricForm(forms.ModelForm):
    class Meta:
        model = DashboardMetric
        fields = (
            "description",
            "pdca_cycle",
            "sgsi_process",
            "method",
            "objective",
            "responsible_text",
            "responsible_position",
            "period",
            "indicator",
            "current_value",
            "action_plan",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "sgsi_process": forms.Textarea(attrs={"rows": 2}),
            "method": forms.Textarea(attrs={"rows": 4}),
            "objective": forms.Textarea(attrs={"rows": 4}),
            "action_plan": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        traducir_formulario(self)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        if self.instance and self.instance.metric_id in {1, 2}:
            self.fields["current_value"].disabled = True
            self.fields["current_value"].help_text = (
                "Este valor proviene de una matriz relacionada y se actualiza desde esa matriz."
            )


class OesiMetricForm(forms.ModelForm):
    class Meta:
        model = OesiMetric
        fields = (
            "description",
            "method",
            "responsible_text",
            "responsible_position",
            "period",
            "indicator",
            "current_value",
            "record_label",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "method": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        traducir_formulario(self)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class StrategicFactorForm(forms.ModelForm):
    class Meta:
        model = StrategicFactor
        fields = (
            "description",
            "weight",
            "classification",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        traducir_formulario(self)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["classification"].widget = forms.Select(
            choices=[(1, "1"), (2, "2"), (3, "3"), (4, "4")],
            attrs={"class": "form-control"},
        )


class DashboardUploadForm(forms.Form):
    version_label = forms.CharField(
        label="Versión / periodo",
        max_length=50,
        required=False,
        help_text="Ejemplo: 2026 o 2026-09.",
    )
    file = forms.FileField(label="Archivo Excel")
    notes = forms.CharField(
        label="Observaciones",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        if not uploaded.name.lower().endswith((".xlsx", ".xlsm")):
            raise forms.ValidationError("Use un archivo .xlsx o .xlsm.")
        head = uploaded.read(4)
        uploaded.seek(0)
        if head[:2] != b"PK":
            raise forms.ValidationError("El archivo no parece ser un Excel válido.")
        return uploaded
