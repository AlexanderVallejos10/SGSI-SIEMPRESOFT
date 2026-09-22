from django.conf import settings
from django.db import models

from apps.controls.models import Control
from apps.core.models import TraceableModel
from apps.documents.models import DocumentVersion, Evidence


class Audit(TraceableModel):
    code = models.CharField(max_length=50, unique=True, db_index=True)
    audit_type = models.CharField(max_length=80)
    scope = models.TextField()
    criteria = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    lead_auditor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="led_audits")
    status = models.CharField(max_length=40, default="planned", db_index=True)
    controls = models.ManyToManyField(Control, blank=True, related_name="audits")
    report = models.ForeignKey(DocumentVersion, null=True, blank=True, on_delete=models.PROTECT, related_name="audit_reports")
    evidence = models.ManyToManyField(Evidence, blank=True, related_name="audits")

    def __str__(self):
        return self.code


class Finding(TraceableModel):
    code = models.CharField(max_length=50, unique=True, db_index=True)
    audit = models.ForeignKey(Audit, on_delete=models.PROTECT, related_name="findings")
    finding_type = models.CharField(max_length=80)
    severity = models.CharField(max_length=40, blank=True)
    control = models.ForeignKey(Control, null=True, blank=True, on_delete=models.PROTECT, related_name="findings")
    criterion = models.TextField(blank=True)
    description = models.TextField()
    evidence = models.ForeignKey(Evidence, null=True, blank=True, on_delete=models.PROTECT, related_name="findings")
    responsible = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assigned_findings")
    status = models.CharField(max_length=40, default="open", db_index=True)
    due_date = models.DateField(null=True, blank=True)


class ImprovementAction(TraceableModel):
    finding = models.ForeignKey(Finding, null=True, blank=True, on_delete=models.PROTECT, related_name="actions")
    description = models.TextField()
    root_cause = models.TextField(blank=True)
    responsible = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="improvement_actions")
    due_date = models.DateField()
    status = models.CharField(max_length=40, default="pending", db_index=True)
    evidence = models.ForeignKey(Evidence, null=True, blank=True, on_delete=models.PROTECT, related_name="improvement_actions")
    effectiveness_verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="verified_improvement_actions")
    effectiveness_verified_at = models.DateTimeField(null=True, blank=True)
    effectiveness_notes = models.TextField(blank=True)
