from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import TraceableModel
from apps.documents.models import Document, Evidence


class Applicability(models.TextChoices):
    APPLICABLE = "applicable", "Aplicable"
    NOT_APPLICABLE = "not_applicable", "No aplicable"
    PENDING = "pending", "Por evaluar"


class ImplementationStatus(models.TextChoices):
    IMPLEMENTED = "implemented", "Implementado"
    IN_PROGRESS = "in_progress", "En proceso"
    PENDING = "pending", "Pendiente"


class ControlFramework(TraceableModel):
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=180)
    version = models.CharField(max_length=40, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.name} {self.version}".strip()


class Control(TraceableModel):
    framework = models.ForeignKey(ControlFramework, on_delete=models.PROTECT, related_name="controls")
    code = models.CharField(max_length=30, db_index=True)
    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=120, blank=True, db_index=True)
    objective = models.TextField(blank=True)
    applicability = models.CharField(max_length=20, choices=Applicability.choices, default=Applicability.PENDING)
    justification = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="owned_controls")
    implementation_status = models.CharField(max_length=20, choices=ImplementationStatus.choices, default=ImplementationStatus.PENDING)
    maturity_level = models.PositiveSmallIntegerField(default=0)
    compliance_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    last_review_at = models.DateField(null=True, blank=True)
    next_review_at = models.DateField(null=True, blank=True)
    documents = models.ManyToManyField(Document, blank=True, related_name="controls")

    class Meta:
        constraints = [models.UniqueConstraint(fields=("framework", "code"), name="uniq_framework_control")]
        ordering = ("framework__code", "code")

    def __str__(self):
        return f"{self.framework.code}:{self.code} - {self.name}"


class ControlEvidence(TraceableModel):
    control = models.ForeignKey(Control, on_delete=models.PROTECT, related_name="evidence_links")
    evidence = models.ForeignKey(Evidence, on_delete=models.PROTECT, related_name="control_links")
    period = models.CharField(max_length=30, blank=True)
    validated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="validated_control_evidence")
    validated_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("control", "evidence", "period"), name="uniq_control_evidence_period")]

from .models_iso import ControlSupportReference, ISOClause, ISODataQualityIssue, ISORequirement

from .models_linking import ControlDocumentAssignment
