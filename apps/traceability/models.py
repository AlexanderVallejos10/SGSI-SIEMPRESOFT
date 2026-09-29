from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TraceableModel


class ImportBatch(TraceableModel):
    name = models.CharField(max_length=255)
    checksum = models.CharField(max_length=64, unique=True)
    kind = models.CharField(max_length=30)
    source = models.FileField(upload_to="traceability/sources/%Y/%m/")


class SourceRow(TraceableModel):
    batch = models.ForeignKey(ImportBatch, on_delete=models.PROTECT, related_name="rows")
    sheet = models.CharField(max_length=100)
    row_number = models.PositiveIntegerField()
    values = models.JSONField(default=list)
    issue = models.TextField(blank=True)
    risk = models.ForeignKey("risks.Risk", null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("batch", "sheet", "row_number"), name="unique_source_row")
        ]


class DocumentLink(TraceableModel):
    KIND = [("owner", "Propietario"), ("access", "Autorización documental")]
    kind = models.CharField(max_length=10, choices=KIND)
    document = models.ForeignKey(
        "documents.Document",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="responsibility_links",
    )
    source_title = models.CharField(max_length=500)
    source_person = models.CharField(max_length=200, blank=True)
    source_position = models.CharField(max_length=250, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="document_links",
    )
    position = models.ForeignKey(
        "organization.Position",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="document_links",
    )
    approved_on = models.DateField(null=True, blank=True)
    source_date = models.CharField(max_length=120, blank=True)
    all_staff = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    source_row = models.ForeignKey(
        SourceRow, null=True, blank=True, on_delete=models.PROTECT, related_name="document_links"
    )

    def clean(self):
        if self.verified and (
            not self.document_id or not (self.user_id or self.position_id or self.all_staff)
        ):
            raise ValidationError("Para verificar, vincule el documento y su persona o cargo autorizado.")
        if self.kind == "owner" and (self.all_staff or (self.verified and not self.user_id)):
            raise ValidationError("La propiedad documental requiere una persona identificada.")

    def __str__(self):
        return self.source_title


class Handover(TraceableModel):
    KINDS = [("entry", "Asignación / ingreso"), ("exit", "Devolución / salida")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="handovers")
    kind = models.CharField(max_length=10, choices=KINDS)
    occurred_on = models.DateField()
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="managed_handovers"
    )
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=12,
        choices=[("draft", "Borrador"), ("issued", "Emitida"), ("signed", "Firmada")],
        default="draft",
    )
    snapshot = models.JSONField(default=dict, blank=True)
    signed_file = models.FileField(upload_to="handovers/signed/%Y/%m/", blank=True)

    def __str__(self):
        return f"ACT-{str(self.pk)[:8].upper()} · {self.get_kind_display()}"


class HandoverItem(TraceableModel):
    handover = models.ForeignKey(Handover, on_delete=models.PROTECT, related_name="items")
    category = models.CharField(
        max_length=20,
        choices=[("material", "Material / equipo"), ("access", "Aplicación / acceso"), ("other", "Otro")],
    )
    description = models.CharField(max_length=250)
    inventory_code = models.CharField(max_length=120, blank=True)
    completed = models.BooleanField(default=False)
    occurred_on = models.DateField(null=True, blank=True)
    delivered_by = models.CharField(max_length=160, blank=True)
    notes = models.TextField(blank=True)
    asset = models.ForeignKey("assets.Asset", null=True, blank=True, on_delete=models.PROTECT)
    access = models.ForeignKey("accounts.SystemAccess", null=True, blank=True, on_delete=models.PROTECT)

    def clean(self):
        if self.access_id and self.handover_id and self.access.user_id != self.handover.user_id:
            raise ValidationError("El acceso debe pertenecer al trabajador del acta.")
        if self.completed and not self.occurred_on:
            raise ValidationError("Indique la fecha del recurso entregado o devuelto.")
