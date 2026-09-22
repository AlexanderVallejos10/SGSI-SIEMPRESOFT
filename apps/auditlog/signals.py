from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.db.models.fields.files import FieldFile
from django.db.models.signals import (
    m2m_changed,
    post_save,
    pre_save,
)
from django.dispatch import receiver

from .context import get_audit_context
from .middleware import get_client_ip
from .services import register_audit_event


# ============================================================
# CONFIGURACIÓN DE AUDITORÍA
# ============================================================

AUDITED_APP_LABELS = {
    "accounts",
    "documents",
    "controls",
    "assets",
    "risks",
    "incidents",
    "assurance",
}


SENSITIVE_FIELDS = {
    "password",
}


IGNORED_UPDATE_FIELDS = {
    "updated_at",
    "last_login",
}


# ============================================================
# SERIALIZACIÓN
# ============================================================

def serialize_value(value):
    """
    Convierte valores de modelos Django a valores que puedan
    almacenarse correctamente dentro de JSON.
    """

    if value is None:
        return None

    if isinstance(value, FieldFile):
        return value.name or ""

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, (datetime, date, time)):
        return value.isoformat()

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


def model_snapshot(instance):
    """
    Obtiene una fotografía de los campos concretos del modelo.

    Las relaciones ForeignKey se almacenan por su ID,
    no serializando el objeto completo.
    """

    data = {}

    for field in instance._meta.concrete_fields:
        field_name = field.name

        if field.is_relation:
            value = getattr(
                instance,
                field.attname,
                None,
            )
        else:
            value = getattr(
                instance,
                field_name,
                None,
            )

        data[field_name] = serialize_value(value)

    return data


# ============================================================
# PROTECCIÓN DE DATOS SENSIBLES
# ============================================================

def safe_value(field_name, value):
    """
    Oculta información sensible antes de almacenarla
    en la bitácora.
    """

    if field_name in SENSITIVE_FIELDS:
        return "<redacted>"

    return value


def safe_snapshot(snapshot):
    """
    Sanitiza todos los campos de una fotografía.
    """

    return {
        field_name: safe_value(
            field_name,
            value,
        )
        for field_name, value in snapshot.items()
    }


# ============================================================
# DETECCIÓN DE CAMBIOS
# ============================================================

def changed_snapshots(before, after):
    """
    Compara BEFORE y AFTER.

    Solo devuelve campos que realmente cambiaron.
    """

    before_changes = {}
    after_changes = {}

    field_names = set(before) | set(after)

    for field_name in field_names:
        if field_name in IGNORED_UPDATE_FIELDS:
            continue

        old_value = before.get(field_name)
        new_value = after.get(field_name)

        if old_value == new_value:
            continue

        before_changes[field_name] = safe_value(
            field_name,
            old_value,
        )

        after_changes[field_name] = safe_value(
            field_name,
            new_value,
        )

    return before_changes, after_changes


# ============================================================
# HELPERS
# ============================================================

def is_audited_model(sender):
    """
    Indica si el modelo pertenece a un módulo auditado.
    """

    return (
        sender._meta.app_label
        in AUDITED_APP_LABELS
    )


def get_business_identifier(instance):
    """
    Obtiene el identificador visible del negocio.

    Prioridad:
    1. business_code
    2. code
    3. PK interna
    """

    for attribute in (
        "business_code",
        "code",
    ):
        value = getattr(
            instance,
            attribute,
            None,
        )

        if value:
            return str(value)

    return str(instance.pk)


# ============================================================
# AUDITORÍA PRE_SAVE
# ============================================================

@receiver(
    pre_save,
    dispatch_uid="sgsi_audit_pre_save",
)
def capture_before_save(
    sender,
    instance,
    raw=False,
    **kwargs,
):
    """
    Captura el estado anterior antes de guardar.

    También completa created_by y updated_by cuando
    el modelo dispone de esos campos.
    """

    if raw:
        return

    if not is_audited_model(sender):
        return

    context = get_audit_context()

    actor = context.user

    if getattr(
        actor,
        "is_authenticated",
        False,
    ):
        if hasattr(
            instance,
            "created_by_id",
        ):
            if (
                instance._state.adding
                and not instance.created_by_id
            ):
                instance.created_by = actor

        if hasattr(
            instance,
            "updated_by_id",
        ):
            instance.updated_by = actor

    # Si el objeto es nuevo no existe un BEFORE.
    if instance._state.adding:
        instance._sgsi_audit_before = {}
        return

    old_instance = (
        sender.objects
        .filter(pk=instance.pk)
        .first()
    )

    if old_instance is None:
        instance._sgsi_audit_before = {}
        return

    instance._sgsi_audit_before = (
        model_snapshot(old_instance)
    )


# ============================================================
# AUDITORÍA POST_SAVE
# ============================================================

@receiver(
    post_save,
    dispatch_uid="sgsi_audit_post_save",
)
def register_after_save(
    sender,
    instance,
    created,
    raw=False,
    **kwargs,
):
    """
    Registra CREATE y UPDATE después de guardar.
    """

    if raw:
        return

    if not is_audited_model(sender):
        return

    # Protección adicional para evitar recursividad.
    if sender._meta.app_label == "auditlog":
        return

    context = get_audit_context()

    after = model_snapshot(instance)

    if created:
        before_payload = {}

        after_payload = safe_snapshot(
            after
        )

        action = "CREATE"

    else:
        before = getattr(
            instance,
            "_sgsi_audit_before",
            {},
        )

        (
            before_payload,
            after_payload,
        ) = changed_snapshots(
            before,
            after,
        )

        # Si no hubo ningún cambio real,
        # no generamos ruido.
        if (
            not before_payload
            and not after_payload
        ):
            return

        action = "UPDATE"

    register_audit_event(
        user=context.user,
        module=sender._meta.app_label,
        action=action,
        entity=sender._meta.label_lower,
        entity_id=get_business_identifier(
            instance
        ),
        before=before_payload,
        after=after_payload,
        result="success",
        ip_address=context.ip_address,
        session_key=context.session_key,
    )


# ============================================================
# MANY TO MANY
# ============================================================

def get_m2m_field_name(
    instance,
    sender,
):
    """
    Determina qué campo ManyToMany provocó
    el evento.
    """

    for field in instance._meta.many_to_many:
        if field.remote_field.through is sender:
            return field.name

    return None


def get_relation_ids(
    instance,
    field_name,
):
    """
    Devuelve los IDs relacionados actualmente
    con el campo ManyToMany.
    """

    if not field_name:
        return []

    manager = getattr(
        instance,
        field_name,
        None,
    )

    if manager is None:
        return []

    return [
        str(pk)
        for pk in manager.values_list(
            "pk",
            flat=True,
        )
    ]


@receiver(
    m2m_changed,
    dispatch_uid="sgsi_audit_m2m_changed",
)
def audit_many_to_many_change(
    sender,
    instance,
    action,
    reverse,
    model,
    pk_set,
    **kwargs,
):
    """
    Registra cambios en relaciones ManyToMany.

    Ejemplos:

    Usuario + Rol
    Riesgo + Control
    Incidente + Evidencia
    Auditoría + Control
    """

    # Trabajamos únicamente desde la relación principal.
    if reverse:
        return

    if (
        instance._meta.app_label
        not in AUDITED_APP_LABELS
    ):
        return

    field_name = get_m2m_field_name(
        instance,
        sender,
    )

    if field_name is None:
        return

    # Antes de clear necesitamos conservar
    # las relaciones existentes.
    if action == "pre_clear":
        instance._sgsi_m2m_before_clear = {
            "field": field_name,
            "related_model": (
                model._meta.label_lower
            ),
            "related_ids": get_relation_ids(
                instance,
                field_name,
            ),
        }

        return

    if action not in {
        "post_add",
        "post_remove",
        "post_clear",
    }:
        return

    context = get_audit_context()

    related_ids = sorted(
        str(pk)
        for pk in (pk_set or set())
    )

    relation_info = {
        "field": field_name,
        "related_model": (
            model._meta.label_lower
        ),
        "related_ids": related_ids,
    }

    # --------------------------------------------------------
    # ADD
    # --------------------------------------------------------

    if action == "post_add":
        audit_action = "RELATION_ADD"

        before = {
            "field": field_name,
            "related_model": (
                model._meta.label_lower
            ),
            "related_ids": [],
        }

        after = relation_info

    # --------------------------------------------------------
    # REMOVE
    # --------------------------------------------------------

    elif action == "post_remove":
        audit_action = "RELATION_REMOVE"

        before = relation_info

        after = {
            "field": field_name,
            "related_model": (
                model._meta.label_lower
            ),
            "related_ids": [],
        }

    # --------------------------------------------------------
    # CLEAR
    # --------------------------------------------------------

    else:
        audit_action = "RELATION_CLEAR"

        before = getattr(
            instance,
            "_sgsi_m2m_before_clear",
            {
                "field": field_name,
                "related_model": (
                    model._meta.label_lower
                ),
                "related_ids": [],
            },
        )

        after = {
            "field": field_name,
            "related_model": (
                model._meta.label_lower
            ),
            "related_ids": [],
        }

    register_audit_event(
        user=context.user,
        module=instance._meta.app_label,
        action=audit_action,
        entity=instance._meta.label_lower,
        entity_id=get_business_identifier(
            instance
        ),
        before=before,
        after=after,
        result="success",
        ip_address=context.ip_address,
        session_key=context.session_key,
    )


# ============================================================
# AUTENTICACIÓN
# ============================================================

def get_request_session_key(request):
    """
    Obtiene la clave de sesión de una petición.
    """

    if request is None:
        return ""

    session = getattr(
        request,
        "session",
        None,
    )

    if session is None:
        return ""

    return session.session_key or ""


def get_request_ip(request):
    """
    Obtiene la IP a partir de una petición.
    """

    if request is None:
        return None

    return get_client_ip(request)


# ============================================================
# LOGIN EXITOSO
# ============================================================

@receiver(
    user_logged_in,
    dispatch_uid="sgsi_audit_user_logged_in",
)
def audit_user_logged_in(
    sender,
    request,
    user,
    **kwargs,
):
    """
    Registra autenticaciones exitosas.
    """

    register_audit_event(
        user=user,
        module="accounts",
        action="LOGIN",
        entity="accounts.user",
        entity_id=get_business_identifier(
            user
        ),
        before={},
        after={
            "event": "login",
        },
        result="success",
        ip_address=get_request_ip(
            request
        ),
        session_key=(
            get_request_session_key(
                request
            )
        ),
    )


# ============================================================
# LOGOUT
# ============================================================

@receiver(
    user_logged_out,
    dispatch_uid="sgsi_audit_user_logged_out",
)
def audit_user_logged_out(
    sender,
    request,
    user,
    **kwargs,
):
    """
    Registra cierres de sesión.
    """

    if user is None:
        return

    register_audit_event(
        user=user,
        module="accounts",
        action="LOGOUT",
        entity="accounts.user",
        entity_id=get_business_identifier(
            user
        ),
        before={
            "event": "authenticated",
        },
        after={
            "event": "logout",
        },
        result="success",
        ip_address=get_request_ip(
            request
        ),
        session_key=(
            get_request_session_key(
                request
            )
        ),
    )


# ============================================================
# LOGIN FALLIDO
# ============================================================

@receiver(
    user_login_failed,
    dispatch_uid="sgsi_audit_user_login_failed",
)
def audit_user_login_failed(
    sender,
    credentials,
    request,
    **kwargs,
):
    """
    Registra intentos fallidos de autenticación.

    Nunca almacena la contraseña enviada.
    """

    identifier = (
        credentials.get("username")
        or credentials.get("email")
        or "<unknown>"
    )

    register_audit_event(
        user=None,
        module="accounts",
        action="LOGIN_FAILED",
        entity="accounts.user",
        entity_id=str(identifier),
        before={},
        after={
            "identifier": str(identifier),
        },
        result="failed",
        ip_address=get_request_ip(
            request
        ),
        session_key=(
            get_request_session_key(
                request
            )
        ),
    )