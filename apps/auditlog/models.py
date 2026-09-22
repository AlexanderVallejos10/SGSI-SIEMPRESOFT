from django.conf import settings
from django.db import models

from apps.core.models import UUIDModel


class AuditLog(UUIDModel):
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    session_key = models.CharField(max_length=80, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    module = models.CharField(max_length=80, db_index=True)
    action = models.CharField(max_length=80, db_index=True)
    entity = models.CharField(max_length=120, db_index=True)
    entity_id = models.CharField(max_length=80, db_index=True)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    result = models.CharField(max_length=30, default="success")
    reason = models.TextField(blank=True)

    class Meta:
        ordering = ("-occurred_at",)
        indexes = [models.Index(fields=("module", "entity", "entity_id"))]

    def __str__(self):
        return f"{self.occurred_at:%Y-%m-%d %H:%M} {self.module}.{self.action}"
