from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.core.models import TraceableModel


class ProcessCategoryKind(models.TextChoices):
    STRATEGIC = "strategic", "Proceso estratégico"
    OPERATIONAL = "operational", "Proceso operativo"
    SUPPORT = "support", "Proceso de apoyo"


class ProcessRelationType(models.TextChoices):
    FLOW = "flow", "Flujo / interacción"
    SUPPORT = "support", "Apoyo"
    GOVERNANCE = "governance", "Gobierno / dirección"
    REFERENCE = "reference", "Referencia"


class ProcessDocumentKind(models.TextChoices):
    SCOPE = "scope", "Documento sobre el alcance del SGSI"
    MAP = "map", "Mapa de procesos"


class ProcessCategory(TraceableModel):
    code = models.CharField(max_length=30, unique=True, db_index=True)
    name = models.CharField(max_length=140)
    kind = models.CharField(
        max_length=20,
        choices=ProcessCategoryKind.choices,
        unique=True,
        db_index=True,
    )
    sort_order = models.PositiveSmallIntegerField(default=100, db_index=True)
    color = models.CharField(max_length=20, default="#dcecf8", blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("sort_order", "name")

    def __str__(self):
        return self.name


class ProcessNode(TraceableModel):
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=180, db_index=True)
    category = models.ForeignKey(
        ProcessCategory,
        on_delete=models.PROTECT,
        related_name="processes",
    )
    description = models.TextField(blank=True)

    owner_position = models.ForeignKey(
        "organization.Position",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="owned_processes",
    )

    involved_areas = models.ManyToManyField(
        "organization.OrganizationalArea",
        blank=True,
        related_name="processes",
    )
    involved_positions = models.ManyToManyField(
        "organization.Position",
        blank=True,
        related_name="involved_processes",
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="participating_processes",
    )

    documents = models.ManyToManyField(
        "documents.Document",
        blank=True,
        related_name="processes",
    )
    controls = models.ManyToManyField(
        "controls.Control",
        blank=True,
        related_name="processes",
    )
    risks = models.ManyToManyField(
        "risks.Risk",
        blank=True,
        related_name="processes",
    )
    assets = models.ManyToManyField(
        "assets.Asset",
        blank=True,
        related_name="processes",
    )

    x = models.PositiveSmallIntegerField(default=100)
    y = models.PositiveSmallIntegerField(default=100)

    is_in_scope = models.BooleanField(default=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("category__sort_order", "y", "x", "name")
        indexes = [
            models.Index(
                fields=("category", "is_active"),
                name="proc_node_cat_active_idx",
            ),
            models.Index(
                fields=("is_in_scope", "is_active"),
                name="proc_node_scope_active_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if self.x > 1120:
            raise ValidationError({"x": "La posición X debe ser <= 1120."})
        if self.y > 650:
            raise ValidationError({"y": "La posición Y debe ser <= 650."})

    @property
    def responsible_area(self):
        if self.owner_position_id and self.owner_position.area_id:
            return self.owner_position.area
        return None

    @property
    def current_owner_user(self):
        if not self.owner_position_id:
            return None
        assignment = (
            self.owner_position.assignments
            .filter(end_date__isnull=True, is_primary=True)
            .select_related("user")
            .first()
        )
        return assignment.user if assignment else None

    def __str__(self):
        return f"{self.code} - {self.name}"


class ProcessRelation(TraceableModel):
    source = models.ForeignKey(
        ProcessNode,
        on_delete=models.PROTECT,
        related_name="outgoing_relations",
    )
    target = models.ForeignKey(
        ProcessNode,
        on_delete=models.PROTECT,
        related_name="incoming_relations",
    )
    relation_type = models.CharField(
        max_length=20,
        choices=ProcessRelationType.choices,
        default=ProcessRelationType.FLOW,
        db_index=True,
    )
    label = models.CharField(max_length=140, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("source__name", "target__name")
        constraints = [
            models.UniqueConstraint(
                fields=("source", "target", "relation_type"),
                name="uniq_process_relation",
            )
        ]

    def clean(self):
        super().clean()
        if self.source_id and self.source_id == self.target_id:
            raise ValidationError(
                "Un proceso no puede relacionarse consigo mismo."
            )

    def __str__(self):
        return f"{self.source.name} → {self.target.name}"


class ProcessCategoryRelation(TraceableModel):
    source = models.ForeignKey(
        ProcessCategory,
        on_delete=models.PROTECT,
        related_name="outgoing_category_relations",
    )
    target = models.ForeignKey(
        ProcessCategory,
        on_delete=models.PROTECT,
        related_name="incoming_category_relations",
    )
    relation_type = models.CharField(
        max_length=20,
        choices=ProcessRelationType.choices,
        default=ProcessRelationType.SUPPORT,
    )
    label = models.CharField(max_length=140, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("source", "target", "relation_type"),
                name="uniq_process_category_relation",
            )
        ]

    def __str__(self):
        return f"{self.source.name} → {self.target.name}"


class ProcessReferenceDocument(TraceableModel):
    slug = models.SlugField(max_length=70, unique=True, db_index=True)
    kind = models.CharField(
        max_length=20,
        choices=ProcessDocumentKind.choices,
        unique=True,
        db_index=True,
    )
    title = models.CharField(max_length=220)
    description = models.TextField(blank=True)
    sort_order = models.PositiveSmallIntegerField(default=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("sort_order", "title")

    def __str__(self):
        return self.title


class ProcessReferenceVersion(TraceableModel):
    document = models.ForeignKey(
        ProcessReferenceDocument,
        on_delete=models.PROTECT,
        related_name="versions",
    )
    version_label = models.CharField(max_length=40)
    file = models.FileField(upload_to="processes/references/%Y/%m/")
    original_name = models.CharField(max_length=255)
    checksum_sha256 = models.CharField(max_length=64, db_index=True)
    notes = models.TextField(blank=True)
    is_current = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ("-is_current", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("document", "checksum_sha256"),
                name="uniq_process_ref_checksum",
            ),
            models.UniqueConstraint(
                fields=("document",),
                condition=Q(is_current=True),
                name="uniq_process_ref_current",
            ),
        ]

    def __str__(self):
        return f"{self.document.title} {self.version_label}"
