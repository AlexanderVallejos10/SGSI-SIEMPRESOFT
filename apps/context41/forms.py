from pathlib import Path

from django import forms

from .models import ContextDocumentKind


class ContextVersionUploadForm(forms.Form):
    version_label = forms.CharField(
        label="Versión",
        max_length=40,
        required=False,
        help_text=(
            "Opcional. Si se deja vacío, el sistema intentará "
            "obtener la versión desde el nombre del archivo."
        ),
    )

    file = forms.FileField(
        label="Nuevo archivo",
    )

    notes = forms.CharField(
        label="Observaciones",
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 3},
        ),
    )

    def __init__(self, *args, document=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.document = document

        for field in self.fields.values():
            field.widget.attrs.setdefault(
                "class",
                "form-control",
            )

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        ext = Path(uploaded.name).suffix.lower()

        if self.document.kind in {
            ContextDocumentKind.MISSION_FODA,
            ContextDocumentKind.ORGANIZATION,
        }:
            allowed = {".pdf"}
        else:
            allowed = {".xlsx", ".xlsm"}

        if ext not in allowed:
            raise forms.ValidationError(
                "Formato no permitido. "
                f"Use: {', '.join(sorted(allowed))}"
            )

        head = uploaded.read(8)
        uploaded.seek(0)

        if ext == ".pdf" and not head.startswith(b"%PDF"):
            raise forms.ValidationError(
                "El archivo seleccionado no parece ser un PDF válido."
            )

        if ext in {".xlsx", ".xlsm"} and not head.startswith(b"PK"):
            raise forms.ValidationError(
                "El archivo seleccionado no parece ser un Excel válido."
            )

        return uploaded
