from django.conf import settings
from django.db import models

from apps.assets.models import Asset
from apps.controls.models import Control
from apps.core.models import TraceableModel
from apps.documents.models import Evidence
from apps.risks.models import Risk


class Severity(models.TextChoices):
    LOW = "low", "Baja"
    MEDIUM = "medium", "Media"
    HIGH = "high", "Alta"
    CRITICAL = "critical", "Crítica"


class Incident(TraceableModel):
    code = models.CharField(max_length=50, unique=True, db_index=True)
    incident_type = models.CharField(max_length=100, db_index=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, db_index=True)
    occurred_at = models.DateTimeField()
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reported_incidents")
    asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.PROTECT, related_name="incidents")
    affected_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="affected_incidents")
    description = models.TextField()
    status = models.CharField(max_length=40, default="reported", db_index=True)
    responsible = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="managed_incidents")
    controls = models.ManyToManyField(Control, blank=True, related_name="incidents")
    risks = models.ManyToManyField(Risk, blank=True, related_name="incidents")
    evidence = models.ManyToManyField(Evidence, blank=True, related_name="incidents")

    class Meta:
        ordering = ("-occurred_at",)


class IncidentEvent(TraceableModel):
    incident = models.ForeignKey(Incident, on_delete=models.PROTECT, related_name="timeline")
    occurred_at = models.DateTimeField()
    action = models.CharField(max_length=160)
    responsible = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="incident_events")
    detail = models.TextField(blank=True)
    evidence = models.ForeignKey(Evidence, null=True, blank=True, on_delete=models.PROTECT, related_name="incident_events")

    class Meta:
        ordering = ("occurred_at",)


class Vulnerability(TraceableModel):
    code = models.CharField(max_length=50, unique=True, db_index=True)
    source = models.CharField(max_length=160)
    cve = models.CharField(max_length=30, blank=True, db_index=True)
    cvss = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="vulnerabilities")
    severity = models.CharField(max_length=20, choices=Severity.choices, db_index=True)
    detected_at = models.DateTimeField()
    responsible = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="vulnerabilities")
    status = models.CharField(max_length=40, default="open", db_index=True)
    due_date = models.DateField(null=True, blank=True)
    solution = models.TextField(blank=True)
    controls = models.ManyToManyField(Control, blank=True, related_name="vulnerabilities")
    risks = models.ManyToManyField(Risk, blank=True, related_name="vulnerabilities")
    evidence = models.ManyToManyField(Evidence, blank=True, related_name="vulnerabilities")
