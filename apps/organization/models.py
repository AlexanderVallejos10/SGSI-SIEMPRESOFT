from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import TraceableModel


class OrganizationRelationType(models.TextChoices):
    LINE = "line", "Jerárquica"
    ASSISTANT = "assistant", "Asistente / apoyo"
    STAFF = "staff", "Staff / asesoría"
    COMMITTEE = "committee", "Comité"


class OrganizationalArea(TraceableModel):
    code = models.CharField(
        max_length=40,
        unique=True,
        db_index=True,
    )
    name = models.CharField(
        max_length=160,
        unique=True,
    )
    description = models.TextField(
        blank=True,
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    color = models.CharField(
        max_length=20,
        default="#dcecf8",
        blank=True,
    )
    sort_order = models.PositiveIntegerField(
        default=100,
        db_index=True,
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = ("sort_order", "name")

    def __str__(self):
        return f"{self.code} - {self.name}"


class Position(TraceableModel):
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )
    title = models.CharField(
        max_length=180,
        db_index=True,
    )
    area = models.ForeignKey(
        OrganizationalArea,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="positions",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    relation_type = models.CharField(
        max_length=20,
        choices=OrganizationRelationType.choices,
        default=OrganizationRelationType.LINE,
        db_index=True,
    )
    sort_order = models.PositiveIntegerField(
        default=100,
        db_index=True,
    )
    max_occupants = models.PositiveSmallIntegerField(
        default=1,
        help_text="0 = sin límite.",
    )
    is_critical = models.BooleanField(
        default=False,
        db_index=True,
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )
    color = models.CharField(
        max_length=20,
        blank=True,
        help_text="Color opcional del cuadro, por ejemplo #d8edf9.",
    )
    description = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ("sort_order", "title")
        indexes = [
            models.Index(
                fields=("parent", "sort_order"),
                name="org_pos_parent_order_idx",
            ),
            models.Index(
                fields=("area", "is_active"),
                name="org_pos_area_active_idx",
            ),
        ]

    def clean(self):
        super().clean()

        if self.parent_id and self.parent_id == self.id:
            raise ValidationError(
                {"parent": "Un puesto no puede depender de sí mismo."}
            )

        current = self.parent
        visited = set()

        while current is not None:
            if current.pk == self.pk:
                raise ValidationError(
                    {"parent": "La jerarquía generaría un ciclo."}
                )

            if current.pk in visited:
                break

            visited.add(current.pk)
            current = current.parent

    @property
    def effective_color(self):
        if self.color:
            return self.color

        if self.area_id and self.area.color:
            return self.area.color

        palette = {
            OrganizationRelationType.LINE: "#eaf4fd",
            OrganizationRelationType.ASSISTANT: "#fff1ef",
            OrganizationRelationType.STAFF: "#f1ecfb",
            OrganizationRelationType.COMMITTEE: "#eceff2",
        }

        return palette.get(
            self.relation_type,
            "#eaf4fd",
        )

    @property
    def is_vacant(self):
        return not self.assignments.filter(
            end_date__isnull=True
        ).exists()

    def __str__(self):
        return f"{self.code} - {self.title}"


class PositionAssignment(TraceableModel):
    position = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="organization_assignments",
    )
    start_date = models.DateField(
        default=timezone.localdate,
    )
    end_date = models.DateField(
        null=True,
        blank=True,
    )
    is_primary = models.BooleanField(
        default=True,
        db_index=True,
    )
    notes = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ("-start_date", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("user",),
                condition=Q(
                    end_date__isnull=True,
                    is_primary=True,
                ),
                name="uniq_active_primary_org_assignment_user",
            )
        ]
        indexes = [
            models.Index(
                fields=("position", "end_date"),
                name="org_asg_pos_active_idx",
            )
        ]

    def clean(self):
        super().clean()

        if (
            self.end_date
            and self.start_date
            and self.end_date < self.start_date
        ):
            raise ValidationError(
                {"end_date": "La fecha final no puede ser anterior al inicio."}
            )

        if (
            self.position_id
            and self.end_date is None
            and self.position.max_occupants
        ):
            active = self.position.assignments.filter(
                end_date__isnull=True
            )

            if self.pk:
                active = active.exclude(pk=self.pk)

            if active.count() >= self.position.max_occupants:
                raise ValidationError(
                    {
                        "position": (
                            "Este puesto alcanzó su capacidad activa. "
                            "Aumente la capacidad o cierre una asignación."
                        )
                    }
                )

    @property
    def is_active(self):
        return self.end_date is None

    def __str__(self):
        return f"{self.position.title} - {self.user}"
