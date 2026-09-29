from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.text import slugify

from .models import (
    OrganizationalArea,
    OrganizationRelationType,
    Position,
    PositionAssignment,
)


User = get_user_model()


def _next_code(model, prefix, text):
    stem = slugify(text or "registro").replace("-", "_").upper()[:24]
    base = f"{prefix}-{stem}" if stem else prefix
    candidate = base[:40]
    counter = 2

    while model.objects.filter(code=candidate).exists():
        suffix = f"-{counter}"
        candidate = f"{base[:40-len(suffix)]}{suffix}"
        counter += 1

    return candidate


class AreaForm(forms.ModelForm):
    positions = forms.ModelMultipleChoiceField(
        label="Puestos del área",
        queryset=Position.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text=(
            "Seleccione puestos existentes sin área. Los trabajadores se vinculan a través de sus puestos. "
            "Desmarcar un puesto lo deja sin área; para trasladarlo desde otra área, use Editar puesto."
        ),
    )

    class Meta:
        model = OrganizationalArea
        fields = (
            "code",
            "name",
            "description",
            "parent",
            "color",
            "sort_order",
            "is_active",
            "positions",
        )
        labels = {
            "code": "Código", "name": "Nombre", "description": "Descripción",
            "parent": "Área superior", "color": "Color", "sort_order": "Orden",
            "is_active": "Área activa",
        }
        widgets = {"color": forms.TextInput(attrs={"type": "color"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["code"].required = False
        available = Q(area__isnull=True, is_active=True)
        if not self.instance._state.adding:
            available |= Q(area=self.instance)
            self.initial["positions"] = self.instance.positions.values_list("pk", flat=True)
        self.fields["positions"].queryset = Position.objects.filter(available).order_by("title")
        self.fields["parent"].queryset = OrganizationalArea.objects.exclude(pk=self.instance.pk)

        for name, field in self.fields.items():
            if name in {"positions", "is_active"}:
                continue
            field.widget.attrs.setdefault(
                "class",
                "form-control",
            )

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("code"):
            cleaned["code"] = _next_code(OrganizationalArea, "AREA", cleaned.get("name"))
        positions = cleaned.get("positions")
        if not cleaned.get("is_active") and positions is not None and positions.filter(is_active=True).exists():
            self.add_error("is_active", "Un área con puestos activos debe permanecer activa.")
        return cleaned


class PositionForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = (
            "code",
            "title",
            "area",
            "parent",
            "relation_type",
            "sort_order",
            "max_occupants",
            "is_critical",
            "is_active",
            "color",
            "description",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["code"].required = False

        if self.instance and self.instance.pk:
            self.fields["parent"].queryset = (
                Position.objects
                .filter(is_active=True)
                .exclude(pk=self.instance.pk)
                .order_by("title")
            )
        else:
            self.fields["parent"].queryset = (
                Position.objects
                .filter(is_active=True)
                .order_by("title")
            )

        self.fields["area"].queryset = (
            OrganizationalArea.objects
            .filter(is_active=True)
            .order_by("sort_order", "name")
        )

        for field in self.fields.values():
            field.widget.attrs.setdefault(
                "class",
                "form-control",
            )

    def clean_code(self):
        code = self.cleaned_data.get("code", "").strip()

        if not code:
            code = _next_code(
                Position,
                "POS",
                self.cleaned_data.get("title"),
            )

        return code


class PositionMoveForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = (
            "parent",
            "area",
            "relation_type",
            "sort_order",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields["parent"].queryset = (
                Position.objects
                .filter(is_active=True)
                .exclude(pk=self.instance.pk)
                .order_by("title")
            )

        self.fields["area"].queryset = (
            OrganizationalArea.objects
            .filter(is_active=True)
            .order_by("sort_order", "name")
        )

        for field in self.fields.values():
            field.widget.attrs.setdefault(
                "class",
                "form-control",
            )


class PositionAssignmentForm(forms.ModelForm):
    class Meta:
        model = PositionAssignment
        fields = (
            "user",
            "start_date",
            "is_primary",
            "notes",
        )
        widgets = {
            "start_date": forms.DateInput(
                attrs={"type": "date"},
            ),
        }

    def __init__(self, *args, position=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.position = position
        self.fields["user"].queryset = (
            User.objects
            .order_by(
                "last_name",
                "first_name",
                "username",
            )
        )

        for field in self.fields.values():
            field.widget.attrs.setdefault(
                "class",
                "form-control",
            )

    def save(self, commit=True):
        assignment = super().save(commit=False)

        if self.position is not None:
            assignment.position = self.position

        if commit:
            assignment.full_clean()
            assignment.save()

        return assignment


class QuickUserForm(forms.Form):
    business_code = forms.CharField(
        label="Código interno",
        max_length=30,
        required=False,
    )
    username = forms.CharField(
        label="Usuario / login",
        max_length=150,
    )
    first_name = forms.CharField(
        label="Nombres",
        max_length=150,
        required=False,
    )
    last_name = forms.CharField(
        label="Apellidos",
        max_length=150,
        required=False,
    )
    email = forms.EmailField(
        label="Correo",
        required=False,
    )
    start_date = forms.DateField(
        label="Fecha de asignación",
        widget=forms.DateInput(
            attrs={"type": "date"},
        ),
    )

    def __init__(self, *args, position=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.position = position

        for field in self.fields.values():
            field.widget.attrs.setdefault(
                "class",
                "form-control",
            )

        if User._meta.get_field("business_code"):
            self.fields["business_code"].required = True

    def clean_username(self):
        username = self.cleaned_data["username"].strip()

        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                "Ya existe un usuario con ese login."
            )

        return username

    def clean_business_code(self):
        code = self.cleaned_data.get("business_code", "").strip()

        try:
            field = User._meta.get_field("business_code")
        except Exception:
            return code

        if not code and not field.blank:
            raise forms.ValidationError(
                "El código interno es obligatorio."
            )

        if code and User.objects.filter(business_code__iexact=code).exists():
            raise forms.ValidationError(
                "Ya existe un usuario con ese código."
            )

        return code
