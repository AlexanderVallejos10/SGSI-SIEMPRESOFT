import uuid

from django.conf import settings
from django.db import models

from apps.core.choices import (
    Classification,
    LifecycleStatus,
)
from apps.core.models import TraceableModel


# ============================================================
# ESTRUCTURA DEL MANUAL SGSI
# ============================================================

class SGSISection(TraceableModel):
    """
    Representa la estructura jerárquica del Manual del SGSI.

    Ejemplos:

        1
        2
        3
        3.1
        3.2
        4
        4.1
        ...
        11

    La estructura se cargará posteriormente desde
    el Manual del SGSI vigente.
    """

    code = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
    )

    title = models.CharField(
        max_length=255,
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )

    sort_order = models.PositiveIntegerField(
        default=0,
        db_index=True,
    )

    description = models.TextField(
        blank=True,
    )

    manual_version = models.CharField(
        max_length=30,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = (
            "sort_order",
            "code",
        )

        verbose_name = "Sección SGSI"
        verbose_name_plural = "Secciones SGSI"

    def __str__(self):
        return f"{self.code} - {self.title}"


# ============================================================
# CALIDAD / PROCEDENCIA DE ARCHIVOS ORIGINALES
# ============================================================

class SourcePackageStatus(models.TextChoices):
    PENDING = (
        "pending",
        "Pendiente de revisión",
    )

    VERIFIED = (
        "verified",
        "Verificado",
    )

    WARNING = (
        "warning",
        "Con observaciones",
    )

    DUPLICATE = (
        "duplicate",
        "Contenido duplicado",
    )


class SourcePackage(TraceableModel):
    """
    Representa el paquete fuente recibido.

    Ejemplos:
        - ZIP exportado de OneDrive
        - lote documental entregado
        - paquete comprimido de evidencias

    Permite conservar la integridad del contenedor
    independientemente de los archivos internos.
    """

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )

    original_name = models.CharField(
        max_length=255,
    )

    original_path = models.TextField(
        blank=True,
    )

    size_bytes = models.BigIntegerField(
        null=True,
        blank=True,
    )

    checksum_sha256 = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
    )

    manifest_sha256 = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text=(
           "SHA-256 calculado sobre el manifiesto "
           "normalizado de archivos internos."
       ),
    )

    duplicate_of = models.ForeignKey(
       "self",
       null=True,
       blank=True,
       on_delete=models.PROTECT,
       related_name="duplicate_packages",
       help_text=(
           "Paquete previamente registrado con "
           "el mismo contenido documental."
       ),
    )

    received_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=SourcePackageStatus.choices,
        default=SourcePackageStatus.PENDING,
        db_index=True,
    )

    notes = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = (
            "original_name",
        )

        verbose_name = "Paquete fuente"
        verbose_name_plural = "Paquetes fuente"

    def __str__(self):
        return (
            f"{self.code} - "
            f"{self.original_name}"
        )

class SourceArtifactKind(models.TextChoices):
    ZIP_MEMBER = (
        "zip_member",
        "Archivo extraído de ZIP",
    )

    STANDALONE = (
        "standalone",
        "Archivo proporcionado directamente",
    )

    GENERATED = (
        "generated",
        "Archivo generado",
    )

    UNKNOWN = (
        "unknown",
        "Origen no determinado",
    )


class SourceQualityStatus(models.TextChoices):
    PENDING = (
        "pending",
        "Pendiente de revisión",
    )

    VERIFIED = (
        "verified",
        "Verificado",
    )

    WARNING = (
        "warning",
        "Con observaciones",
    )

    DUPLICATE = (
        "duplicate",
        "Duplicado",
    )

    INVALID = (
        "invalid",
        "Dato o archivo inválido",
    )


class SourceArtifact(TraceableModel):
    """
    Inventario maestro de archivos fuente.

    Un SourceArtifact representa el archivo tal como
    fue recibido o encontrado dentro de un ZIP.

    No implica todavía que el archivo sea un documento
    controlado o una evidencia. Esa clasificación
    se realiza mediante sus relaciones posteriores.
    """

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )

    original_name = models.CharField(
        max_length=255,
    )

    original_path = models.TextField(
        blank=True,
        help_text=(
            "Ruta original dentro del ZIP o repositorio."
        ),
    )

    source_archive = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            "Nombre del ZIP u origen del que provino."
        ),
    )

    source_package = models.ForeignKey(
        SourcePackage,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="artifacts",
        help_text=(
            "Paquete ZIP o lote documental "
            "del cual provino el archivo."
        ),
     )

    source_kind = models.CharField(
        max_length=30,
        choices=SourceArtifactKind.choices,
        default=SourceArtifactKind.UNKNOWN,
    )

    extension = models.CharField(
        max_length=30,
        blank=True,
    )

    mime_type = models.CharField(
        max_length=160,
        blank=True,
    )

    size_bytes = models.BigIntegerField(
        null=True,
        blank=True,
    )

    checksum_sha256 = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
    )

    source_modified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    file = models.FileField(
        upload_to="source_artifacts/%Y/%m/",
        null=True,
        blank=True,
    )

    source_verified = models.BooleanField(
        default=False,
    )

    quality_status = models.CharField(
        max_length=30,
        choices=SourceQualityStatus.choices,
        default=SourceQualityStatus.PENDING,
        db_index=True,
    )

    quality_notes = models.TextField(
        blank=True,
    )

    duplicate_of = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="duplicate_copies",
    )

    class Meta:
        ordering = (
            "source_archive",
            "original_path",
            "original_name",
        )

        indexes = [
            models.Index(
                fields=["source_kind"],
            ),
            models.Index(
                fields=["quality_status"],
            ),
            models.Index(
                fields=["extension"],
            ),
        ]

        verbose_name = "Archivo fuente"
        verbose_name_plural = "Inventario maestro de archivos"

    def __str__(self):
        return (
            f"{self.code} - "
            f"{self.original_name}"
        )


# ============================================================
# DOCUMENTOS CONTROLADOS
# ============================================================

class Document(TraceableModel):
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )

    source_identity_key = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        help_text=(
            "Huella estable de la identidad documental importada. "
            "Permite reejecutar la promoción sin duplicar documentos."
        ),
    )

    title = models.CharField(
        max_length=255,
    )

    category = models.CharField(
        max_length=100,
        blank=True,
    )

    document_type = models.CharField(
        max_length=100,
        blank=True,
    )

    management_system = models.CharField(
        max_length=30,
        default="SGSI",
        db_index=True,
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="owned_documents",
        help_text=(
            "Responsable documental. Puede quedar pendiente "
            "durante una importación histórica."
        ),
    )

    classification = models.CharField(
        max_length=20,
        choices=Classification.choices,
        default=Classification.INTERNAL,
    )

    status = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=LifecycleStatus.choices,
        default=None,
    )

    next_review_at = models.DateField(
        null=True,
        blank=True,
    )

    retention_policy = models.CharField(
        max_length=150,
        blank=True,
    )

    sgsi_sections = models.ManyToManyField(
        SGSISection,
        blank=True,
        related_name="documents",
        help_text=(
            "Numerales del Manual del SGSI "
            "sustentados por este documento."
        ),
    )

    class Meta:
        ordering = (
            "code",
        )

    def __str__(self):
        return f"{self.code} - {self.title}"


# ============================================================
# VERSIONES DOCUMENTALES
# ============================================================

class DocumentVersion(TraceableModel):
    document = models.ForeignKey(
        Document,
        on_delete=models.PROTECT,
        related_name="versions",
    )

    version = models.CharField(
        max_length=30,
    )

    file = models.FileField(
        upload_to="documents/%Y/%m/",
    )

    checksum_sha256 = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
    )

    source_artifact = models.ForeignKey(
        SourceArtifact,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="document_versions",
        help_text=(
            "Archivo original del inventario maestro "
            "del cual provino esta versión."
        ),
    )

    change_reason = models.TextField(
        blank=True,
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="authored_document_versions",
    )

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reviewed_document_versions",
    )

    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="approved_document_versions",
    )

    issue_date = models.DateField(
        null=True,
        blank=True,
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=LifecycleStatus.choices,
        default=None,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=(
                    "document",
                    "version",
                ),
                name="uniq_document_version",
            )
        ]

        ordering = (
            "document__code",
            "-created_at",
        )

    def __str__(self):
        return (
            f"{self.document.code} "
            f"v{self.version}"
        )


# ============================================================
# EVIDENCIAS
# ============================================================

class Evidence(TraceableModel):
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )

    description = models.CharField(
        max_length=255,
    )

    source = models.CharField(
        max_length=160,
        blank=True,
    )

    evidence_date = models.DateField(
        null=True,
        blank=True,
    )

    file = models.FileField(
        upload_to="evidence/%Y/%m/",
        null=True,
        blank=True,
    )

    external_reference = models.URLField(
        blank=True,
    )

    checksum_sha256 = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
    )

    source_artifact = models.ForeignKey(
        SourceArtifact,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="evidence_records",
        help_text=(
            "Archivo original del inventario maestro "
            "que sustenta esta evidencia."
        ),
    )

    classification = models.CharField(
        max_length=20,
        choices=Classification.choices,
        default=Classification.INTERNAL,
    )

    document_version = models.ForeignKey(
        DocumentVersion,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="evidence_records",
    )

    class Meta:
        ordering = (
            "code",
        )

    def __str__(self):
        return (
            f"{self.code} - "
            f"{self.description}"
        )

from .models_classification import SourceArtifactClassification

from .models_promotion import DocumentImportIssue, DocumentVersionRepresentation

from .models_mapping import DocumentSectionAssignment


class ManualDocumentRequirement(models.Model):
    """Documento que el Manual del SGSI exige en un numeral. Se edita desde /admin/ cuando cambia el Manual."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numeral = models.CharField(max_length=20, db_index=True, verbose_name="Numeral")
    name = models.CharField(max_length=255, verbose_name="Documento, tal como lo nombra el Manual")
    location = models.TextField(blank=True, verbose_name="Ubicación según el Manual")
    manual_version = models.CharField(max_length=20, blank=True, verbose_name="Versión del Manual")
    sort_order = models.PositiveSmallIntegerField(default=10, verbose_name="Orden")
    is_active = models.BooleanField(default=True, verbose_name="Vigente")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("numeral", "sort_order", "name")
        verbose_name = "Documento exigido por el Manual"
        verbose_name_plural = "Documentos exigidos por el Manual"

    def __str__(self):
        return f"{self.numeral} · {self.name}"


class ManualReference(models.Model):
    """Versión del Manual del SGSI que se muestra en todas las cláusulas. Cada cambio es una fila nueva:
    queda el historial de quién la cambió, cuándo y por qué (control documental, 7.5)."""

    STATUS = (("Borrador", "Borrador"), ("Vigente", "Vigente"), ("En revisión", "En revisión"))

    title = models.CharField(max_length=200, default="Manual del Sistema de Gestión de Seguridad de la Información")
    version = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS, default="Borrador")
    issue_date = models.DateField(null=True, blank=True)
    prepared_by = models.CharField(max_length=120, blank=True)
    approved_by = models.CharField(max_length=120, blank=True)
    change_note = models.TextField(blank=True)
    is_current = models.BooleanField(default=True, db_index=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-changed_at",)
        verbose_name = "Versión del Manual del SGSI"
        verbose_name_plural = "Versiones del Manual del SGSI"
        constraints = [models.UniqueConstraint(fields=("is_current",), condition=models.Q(is_current=True), name="uniq_current_manual_reference")]

    def __str__(self):
        return f"{self.title} v{self.version} ({self.status})"
