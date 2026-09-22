import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import TraceableModel


# ============================================================
# USUARIOS
# ============================================================

class UserStatus(models.TextChoices):
    ACTIVE = "active", "Activo"
    BLOCKED = "blocked", "Bloqueado"
    INACTIVE = "inactive", "Inactivo"
    UNKNOWN = "unknown", "Estado no confirmado"


class User(AbstractUser):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    business_code = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
    )

    document_number = models.CharField(
        max_length=40,
        blank=True,
    )

    area = models.CharField(
        max_length=120,
        blank=True,
    )

    position = models.CharField(
        max_length=120,
        blank=True,
    )

    manager = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="team_members",
    )

    employment_start = models.DateField(
        null=True,
        blank=True,
    )

    employment_end = models.DateField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=UserStatus.choices,
        default=UserStatus.ACTIVE,
    )

    status_as_of = models.DateField(
        null=True,
        blank=True,
        help_text=(
            "Fecha en la que la fuente documental "
            "confirma el estado registrado."
        ),
    )

    source_document = models.CharField(
        max_length=255,
        blank=True,
    )

    source_reference = models.CharField(
        max_length=255,
        blank=True,
    )

    source_verified = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return (
            f"{self.business_code} - "
            f"{self.get_full_name() or self.username}"
        )


# ============================================================
# SISTEMAS CORPORATIVOS
# ============================================================

class CorporateSystemStatus(models.TextChoices):
    ACTIVE = "active", "Activo"
    INACTIVE = "inactive", "Inactivo"
    UNKNOWN = "unknown", "Estado no confirmado"


class CorporateSystem(TraceableModel):
    business_code = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
    )

    name = models.CharField(
        max_length=200,
        unique=True,
    )

    category = models.CharField(
        max_length=120,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    authorization_authority = models.CharField(
        max_length=200,
        blank=True,
        help_text=(
            "Cargo o autoridad que puede aprobar "
            "o retirar el acceso."
        ),
    )

    technical_implementer = models.CharField(
        max_length=200,
        blank=True,
        help_text=(
            "Cargo o responsable que implementa "
            "técnicamente el acceso."
        ),
    )

    review_frequency = models.CharField(
        max_length=250,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=CorporateSystemStatus.choices,
        default=CorporateSystemStatus.ACTIVE,
    )

    status_as_of = models.DateField(
    	null=True,
   	 blank=True,
   	 help_text=(
      	  "Fecha en la que la fuente documental "
      	  "confirma el estado registrado."
         ),
     )

    source_document = models.CharField(
        max_length=255,
        blank=True,
    )

    source_reference = models.CharField(
        max_length=255,
        blank=True,
    )

    source_verified = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = (
            "business_code",
        )

        indexes = [
            models.Index(
                fields=["name"],
            ),
            models.Index(
                fields=["status"],
            ),
        ]

        verbose_name = "Sistema corporativo"
        verbose_name_plural = "Sistemas corporativos"

    def __str__(self):
        return (
            f"{self.business_code} - "
            f"{self.name}"
        )


# ============================================================
# ACCESOS A SISTEMAS
# ============================================================

class SystemAccessStatus(models.TextChoices):
    REQUESTED = "requested", "Solicitado"
    ACTIVE = "active", "Activo"
    SUSPENDED = "suspended", "Suspendido"
    REVOKED = "revoked", "Revocado"
    EXPIRED = "expired", "Vencido"
    UNKNOWN = "unknown", "Estado no confirmado"


class SystemAccess(TraceableModel):
    business_code = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
    )

    user = models.ForeignKey(
        "User",
        on_delete=models.PROTECT,
        related_name="system_accesses",
    )

    system = models.ForeignKey(
        CorporateSystem,
        on_delete=models.PROTECT,
        related_name="user_accesses",
    )

    role_profile = models.CharField(
        max_length=200,
        blank=True,
    )

    access_level = models.CharField(
        max_length=200,
        blank=True,
    )

    is_privileged = models.BooleanField(
        null=True,
        blank=True,
        help_text=(
            "NULL: la fuente no permite confirmar "
            "si el acceso es privilegiado."
        ),
    )

    mfa_enabled = models.BooleanField(
        null=True,
        blank=True,
        help_text=(
            "NULL: la fuente no permite confirmar "
            "el estado de MFA."
        ),
    )

    authorization_date = models.DateField(
        null=True,
        blank=True,
    )

    approved_by = models.ForeignKey(
        "User",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="approved_system_accesses",
    )

    approval_reference = models.CharField(
        max_length=255,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=SystemAccessStatus.choices,
        default=SystemAccessStatus.REQUESTED,
    )

    status_as_of = models.DateField(
        null=True,
        blank=True,
        help_text=(
            "Fecha en que la evidencia confirma "
            "el estado indicado."
        ),
    )

    last_review_at = models.DateField(
        null=True,
        blank=True,
    )

    next_review_at = models.DateField(
        null=True,
        blank=True,
    )

    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    source_document = models.CharField(
        max_length=255,
        blank=True,
    )

    source_reference = models.CharField(
        max_length=255,
        blank=True,
    )

    source_verified = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = (
            "user__business_code",
            "system__business_code",
        )

        indexes = [
            models.Index(
                fields=["status"],
            ),
            models.Index(
                fields=["is_privileged"],
            ),
            models.Index(
                fields=["mfa_enabled"],
            ),
            models.Index(
                fields=["next_review_at"],
            ),
            models.Index(
                fields=["status_as_of"],
            ),
        ]

        verbose_name = "Acceso a sistema"
        verbose_name_plural = "Accesos a sistemas"

    def __str__(self):
        return (
            f"{self.business_code} - "
            f"{self.user.business_code} / "
            f"{self.system.name}"
        )


# ============================================================
# REVISIONES DE ACCESO
# ============================================================

class AccessReviewDecision(models.TextChoices):
    KEEP = "keep", "Mantener"
    MODIFY = "modify", "Modificar"
    REVOKE = "revoke", "Revocar"


class AccessReview(TraceableModel):
    business_code = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
    )

    access = models.ForeignKey(
        SystemAccess,
        on_delete=models.PROTECT,
        related_name="reviews",
    )

    reviewer = models.ForeignKey(
        "User",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="performed_access_reviews",
    )

    reviewed_at = models.DateField()

    decision = models.CharField(
        max_length=20,
        choices=AccessReviewDecision.choices,
    )

    comments = models.TextField(
        blank=True,
    )

    evidence_reference = models.CharField(
        max_length=255,
        blank=True,
    )

    next_review_at = models.DateField(
        null=True,
        blank=True,
    )

    source_document = models.CharField(
        max_length=255,
        blank=True,
    )

    source_reference = models.CharField(
        max_length=255,
        blank=True,
    )

    source_verified = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = (
            "-reviewed_at",
        )

        indexes = [
            models.Index(
                fields=["decision"],
            ),
            models.Index(
                fields=["reviewed_at"],
            ),
            models.Index(
                fields=["next_review_at"],
            ),
        ]

        verbose_name = "Revisión de acceso"
        verbose_name_plural = "Revisiones de acceso"

    def __str__(self):
        return (
            f"{self.business_code} - "
            f"{self.access.business_code} - "
            f"{self.get_decision_display()}"
        )