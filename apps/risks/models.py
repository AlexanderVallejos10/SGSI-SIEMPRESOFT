from django.conf import settings
from django.db import models

from apps.assets.models import Asset
from apps.controls.models import Control
from apps.core.models import TraceableModel
from apps.documents.models import Evidence


class RiskStatus(models.TextChoices):
    IDENTIFIED = "identified", "Identificado"
    TREATMENT = "treatment", "En tratamiento"
    ACCEPTED = "accepted", "Aceptado"
    CLOSED = "closed", "Cerrado"


class Risk(TraceableModel):
    origin = models.CharField(max_length=120, blank=True)
    category = models.CharField(max_length=100, blank=True)
    event = models.TextField(blank=True)
    motivation = models.TextField(blank=True)
    existing_controls = models.TextField(blank=True)
    owner_position = models.ForeignKey(
        "organization.Position", null=True, blank=True, on_delete=models.PROTECT, related_name="owned_risks"
    )
    is_active = models.BooleanField(default=True)

    code = models.CharField(max_length=50, unique=True, db_index=True)
    process = models.CharField(max_length=160, db_index=True)
    asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.PROTECT, related_name="risks")
    scenario = models.TextField()
    threat = models.CharField(max_length=255, blank=True)
    vulnerability = models.CharField(max_length=255, blank=True)
    consequence = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="owned_risks"
    )
    controls = models.ManyToManyField(Control, blank=True, related_name="risks")
    status = models.CharField(
        max_length=20, choices=RiskStatus.choices, default=RiskStatus.IDENTIFIED, db_index=True
    )
    identified_at = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.code} - {self.process}"


class RiskAssessment(TraceableModel):
    risk = models.ForeignKey(Risk, on_delete=models.PROTECT, related_name="assessments")
    assessed_at = models.DateTimeField()
    probability = models.PositiveSmallIntegerField()
    impact = models.PositiveSmallIntegerField()
    inherent_score = models.DecimalField(max_digits=8, decimal_places=2)
    residual_probability = models.PositiveSmallIntegerField(null=True, blank=True)
    residual_impact = models.PositiveSmallIntegerField(null=True, blank=True)
    residual_score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("-assessed_at",)


class RiskTreatment(TraceableModel):
    start_date = models.DateField(null=True, blank=True)
    closed_date = models.DateField(null=True, blank=True)
    source_start = models.CharField(max_length=100, blank=True)
    source_end = models.CharField(max_length=100, blank=True)
    residual_probability = models.PositiveSmallIntegerField(null=True, blank=True)
    residual_impact = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    risk = models.ForeignKey(Risk, on_delete=models.PROTECT, related_name="treatments")
    option = models.CharField(max_length=60)
    action = models.TextField()
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="risk_treatments",
    )
    resources = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=30, default="pending")
    evidence = models.ForeignKey(
        Evidence, null=True, blank=True, on_delete=models.PROTECT, related_name="risk_treatments"
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="approved_risk_treatments",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
