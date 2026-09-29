from pathlib import Path

from django import forms

from .models import ProcessNode, ProcessRelation


class ProcessNodeForm(forms.ModelForm):
    class Meta:
        model = ProcessNode
        fields = (
            "code",
            "name",
            "category",
            "description",
            "primary_area",
            "owner_position",
            "involved_areas",
            "involved_positions",
            "participants",
            "documents",
            "controls",
            "risks",
            "assets",
            "is_in_scope",
            "is_external",
            "is_active",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "involved_areas": forms.SelectMultiple(attrs={"size": 7}),
            "involved_positions": forms.SelectMultiple(attrs={"size": 7}),
            "participants": forms.SelectMultiple(attrs={"size": 7}),
            "documents": forms.SelectMultiple(attrs={"size": 8}),
            "controls": forms.SelectMultiple(attrs={"size": 8}),
            "risks": forms.SelectMultiple(attrs={"size": 8}),
            "assets": forms.SelectMultiple(attrs={"size": 8}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class QuickProcessForm(forms.ModelForm):
    class Meta:
        model = ProcessNode
        fields = (
            "code",
            "name",
            "category",
            "primary_area",
            "owner_position",
            "description",
            "is_in_scope",
            "is_external",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class ProcessRelationForm(forms.ModelForm):
    class Meta:
        model = ProcessRelation
        fields = (
            "source",
            "target",
            "relation_type",
            "label",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class ReferenceVersionUploadForm(forms.Form):
    version_label = forms.CharField(
        label="Versión",
        max_length=40,
        required=False,
        help_text=(
            "Opcional. Si se deja vacío, se intenta detectar "
            "la versión desde el nombre del PDF."
        ),
    )
    file = forms.FileField(label="Nuevo PDF")
    notes = forms.CharField(
        label="Observaciones",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, document=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.document = document
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        ext = Path(uploaded.name).suffix.lower()

        if ext != ".pdf":
            raise forms.ValidationError(
                "Este documento debe cargarse en formato PDF."
            )

        head = uploaded.read(8)
        uploaded.seek(0)

        if not head.startswith(b"%PDF"):
            raise forms.ValidationError(
                "El archivo seleccionado no parece ser un PDF válido."
            )

        return uploaded
