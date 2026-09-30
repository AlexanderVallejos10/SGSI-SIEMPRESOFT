from django.utils import timezone
from django.conf import settings
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

    # ---- foto de perfil (nombre de archivo aleatorio; se sirve solo a usuarios con sesión)
    photo = models.FileField(upload_to="avatares/", blank=True)

    # ---- acceso al sistema
    must_change_password = models.BooleanField(
        default=False,
        help_text="Debe cambiar la contraseña al ingresar (credenciales nuevas o restablecidas).",
    )
    password_changes = models.PositiveIntegerField(
        default=0,
        help_text="Veces que el usuario cambió su contraseña por su cuenta.",
    )
    password_changed_at = models.DateTimeField(null=True, blank=True)
    credentials_issued_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True, db_index=True)

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


# ======================================================================
# Acceso al sistema: sesiones, intentos de ingreso, solicitudes de cambio
# de contraseña y notificaciones.
# ======================================================================


class UserSession(models.Model):
    """Una conexión al sistema: desde que ingresa hasta que sale o vence por inactividad."""

    ENDED_REASONS = (
        ("logout", "Cerró sesión"),
        ("inactividad", "Cerrada por inactividad"),
        ("reemplazada", "Reemplazada por un nuevo ingreso"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="connection_sessions")
    session_key = models.CharField(max_length=64, db_index=True)
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_seen_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True, db_index=True)
    ended_reason = models.CharField(max_length=20, choices=ENDED_REASONS, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("-started_at",)
        verbose_name = "Sesión de usuario"
        verbose_name_plural = "Sesiones de usuarios"

    @property
    def duration(self):
        return (self.ended_at or self.last_seen_at) - self.started_at

    def __str__(self):
        return f"{self.user} · {self.started_at:%d/%m/%Y %H:%M}"


class LoginAttempt(models.Model):
    """Cada intento de ingreso. Sirve para bloquear ataques de fuerza bruta y para auditoría."""

    username = models.CharField(max_length=150, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    success = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Intento de ingreso"
        verbose_name_plural = "Intentos de ingreso"


class PasswordChangeRequest(models.Model):
    STATUS = (("pending", "Pendiente"), ("approved", "Aprobada"), ("rejected", "Rechazada"))

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="password_requests")
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS, default="pending", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Solicitud de cambio de contraseña"
        verbose_name_plural = "Solicitudes de cambio de contraseña"


class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    kind = models.CharField(max_length=40, db_index=True)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    url = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("recipient", "read_at"), name="acc_notif_unread_idx")]
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
