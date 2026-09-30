from django.conf import settings
from django.db import models

from apps.core.choices import Classification
from apps.core.models import TraceableModel
from apps.documents.models import DocumentVersion, Evidence


class AssetStatus(models.TextChoices):
    AVAILABLE = "available", "Disponible"
    ASSIGNED = "assigned", "Asignado"
    MAINTENANCE = "maintenance", "Mantenimiento"
    REVIEW = "review", "Revisión"
    RETIRED = "retired", "Baja"


class AssetClass(models.TextChoices):
    EQUIPMENT = "equipment", "Equipo"
    INFORMATION = "information", "Activo de información (primario)"
    SUPPORT = "support", "Activo de soporte"
    TECHNOLOGY = "technology", "Activo tecnológico"
    BYOD = "byod", "Dispositivo personal (BYOD)"
    DISPOSED = "disposed", "Soporte dado de baja"


class Asset(TraceableModel):
    code = models.CharField(max_length=50, unique=True, db_index=True)
    asset_type = models.CharField(max_length=80, db_index=True)
    name = models.CharField(max_length=180)
    brand = models.CharField(max_length=80, blank=True)
    model = models.CharField(max_length=100, blank=True)
    serial = models.CharField(max_length=120, blank=True, db_index=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="owned_assets")
    custodian = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="custodied_assets")
    location = models.CharField(max_length=160, blank=True)
    classification = models.CharField(max_length=20, choices=Classification.choices, default=Classification.INTERNAL)
    criticality = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=20, choices=AssetStatus.choices, default=AssetStatus.AVAILABLE, db_index=True)
    operating_system = models.CharField(max_length=120, blank=True)
    encrypted = models.BooleanField(null=True, blank=True)
    edr_antivirus = models.CharField(max_length=120, blank=True)
    mdm = models.CharField(max_length=120, blank=True)
    patch_status = models.CharField(max_length=80, blank=True)
    # Datos para la trazabilidad pedida por el SGSI (quién lo tiene, dónde está, de dónde sale el dato).
    asset_class = models.CharField(max_length=20, choices=AssetClass.choices, default=AssetClass.EQUIPMENT, db_index=True)
    area = models.CharField(max_length=160, blank=True)
    process = models.CharField(max_length=160, blank=True)
    hostname = models.CharField(max_length=120, blank=True, db_index=True)
    owner_role = models.CharField(max_length=160, blank=True, help_text="Propietario según la matriz de riesgos (cargo).")
    custodian_name = models.CharField(max_length=160, blank=True, help_text="Responsable cuando aún no tiene usuario en el sistema.")
    confidentiality = models.CharField(max_length=40, blank=True)
    integrity = models.CharField(max_length=40, blank=True)
    availability = models.CharField(max_length=40, blank=True)
    valuation = models.CharField(max_length=20, blank=True)
    source = models.CharField(max_length=255, blank=True, help_text="Archivo de origen del dato.")
    extra = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.code} - {self.name}"


class MovementType(models.TextChoices):
    ASSIGNMENT = "assignment", "Asignación"
    DELIVERY = "delivery", "Entrega"
    RETURN = "return", "Devolución"
    TRANSFER = "transfer", "Transferencia"
    REPLACEMENT = "replacement", "Reemplazo"
    MAINTENANCE = "maintenance", "Mantenimiento"
    RETIREMENT = "retirement", "Baja"
    CHECKOUT = "checkout", "Salida de la oficina"
    CHECKIN = "checkin", "Retorno a la oficina"


class AssetMovement(TraceableModel):
    movement_type = models.CharField(max_length=20, choices=MovementType.choices, db_index=True)
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="movements")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="asset_movements")
    origin = models.CharField(max_length=160, blank=True)
    destination = models.CharField(max_length=160, blank=True)
    occurred_at = models.DateTimeField()
    reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    document_version = models.ForeignKey(DocumentVersion, null=True, blank=True, on_delete=models.PROTECT, related_name="asset_movements")
    replaced_asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.PROTECT, related_name="replacement_movements")
    evidence = models.ForeignKey(Evidence, null=True, blank=True, on_delete=models.PROTECT, related_name="asset_movements")
    person_name = models.CharField(max_length=160, blank=True)
    source = models.CharField(max_length=255, blank=True)
    import_key = models.CharField(max_length=120, blank=True, db_index=True)

    class Meta:
        ordering = ("-occurred_at",)


class Maintenance(TraceableModel):
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="maintenances")
    maintenance_type = models.CharField(max_length=80)
    performed_at = models.DateTimeField()
    technician = models.CharField(max_length=160)
    result = models.TextField()
    next_due_at = models.DateField(null=True, blank=True)
    evidence = models.ForeignKey(Evidence, null=True, blank=True, on_delete=models.PROTECT, related_name="maintenances")
    person_name = models.CharField(max_length=160, blank=True, help_text="Persona revisada o a cargo del equipo.")
    source = models.CharField(max_length=255, blank=True)
    import_key = models.CharField(max_length=120, blank=True, db_index=True)

    class Meta:
        ordering = ("-performed_at",)


class AssetSoftwareSnapshot(TraceableModel):
    """Inventario de software de un equipo exportado de Microsoft Defender en una fecha."""

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="software_snapshots")
    taken_at = models.DateField()
    items = models.JSONField(default=list)
    total = models.PositiveIntegerField(default=0)
    weaknesses = models.PositiveIntegerField(default=0)
    exploitable = models.PositiveIntegerField(default=0)
    source = models.CharField(max_length=255, blank=True)
    import_key = models.CharField(max_length=120, blank=True, db_index=True)

    class Meta:
        ordering = ("-taken_at",)
