from django import forms

from .models import Context42DocumentVersion


class Context42VersionUploadForm(forms.ModelForm):
    class Meta:
        model = Context42DocumentVersion
        fields = ("file", "version_label", "notes")
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, document=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.document = document
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["file"].help_text = "Sube una nueva versión del archivo. Se conservará el historial y esta versión quedará vigente."