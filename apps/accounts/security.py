"""Reglas de acceso al sistema del SGSI.

- Administran el SGSI (editan todo, asignan permisos, generan credenciales, aprueban solicitudes y
  ubican personas en el organigrama): el Gerente General y el Oficial / Jefe de Seguridad de la
  Información, es decir, quienes tienen el rol «Administrador SGSI» (o un superusuario técnico).
- Credenciales: usuario y contraseña temporal generados automáticamente; se cambia al primer ingreso.
- Cambio de contraseña: los administradores, cuando quieran. Los demás, una sola vez; después
  deben enviar una solicitud que aprueba un administrador.
Todo evento queda en el registro de auditoría.
"""

import secrets
import unicodedata

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.auditlog.services import register_audit_event

from .models import Notification, PasswordChangeRequest

ADMIN_ROLE = "Administrador SGSI"
DEFAULT_ROLE = "Usuario / Colaborador"

# Permisos por módulo que se pueden marcar con casillas («Ver» y «Editar»).
MODULES = [
    ("documentos", "Documentos y Manual", ["documents.document", "documents.documentversion", "documents.manualdocumentrequirement"]),
    ("contexto", "Contexto (4.1 y 4.2)", ["context41.contextdocument", "context42.context42document"]),
    ("organizacion", "Organización y organigrama", ["organization.organizationalarea", "organization.position", "organization.positionassignment"]),
    ("procesos", "Procesos", ["processes.processnode", "processes.processrelation"]),
    ("riesgos", "Riesgos y tratamientos", ["risks.risk", "risks.riskassessment", "risks.risktreatment"]),
    ("activos", "Activos y equipos", ["assets.asset", "assets.assetmovement", "assets.maintenance"]),
    ("incidentes", "Incidentes y vulnerabilidades", ["incidents.incident", "incidents.vulnerability"]),
    ("auditorias", "Auditorías y mejoras", ["assurance.audit", "assurance.finding", "assurance.improvementaction"]),
    ("controles", "Controles del Anexo A", ["controls.control"]),
    ("registros", "Registros del SGSI", ["registers.registerentry"]),
    ("tablero", "Tablero del SGSI", ["dashboard_live.dashboardmetric", "dashboard_live.oesimetric", "dashboard_live.strategicfactor",
                                     "dashboard_live.oeeosialignment", "dashboard_live.requirementosialignment"]),
    ("responsabilidades", "Responsabilidades documentales", ["traceability.documentlink"]),
]
EXTRA_EDIT_PERMS = {"registros": ["registers.import_registerentry"]}

READABLE = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sin 0/O, 1/l/I


# ---------------------------------------------------------------- roles
def is_sgsi_admin(user):
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return False
    if user.is_superuser:
        return True
    cached = getattr(user, "_sgsi_admin", None)
    if cached is None:
        cached = user.groups.filter(name=ADMIN_ROLE).exists()
        user._sgsi_admin = cached
    return cached


def sgsi_admins():
    User = get_user_model()
    return User.objects.filter(is_active=True).filter(Q(is_superuser=True) | Q(groups__name=ADMIN_ROLE)).distinct()


# ---------------------------------------------------------------- notificaciones
def notify(recipients, *, kind, title, body="", url="", actor=None):
    items = [
        Notification(recipient=r, actor=actor, kind=kind, title=title[:200], body=body, url=url[:300])
        for r in {r.pk: r for r in recipients if r is not None}.values()
    ]
    Notification.objects.bulk_create(items)
    return len(items)


def _audit(actor, action, user, before=None, after=None, reason="", request=None):
    register_audit_event(
        user=actor, module="accounts", action=action, entity="User", entity_id=user.pk,
        before=before or {}, after=after or {}, reason=reason,
        ip_address=client_ip(request) if request else None,
        session_key=getattr(getattr(request, "session", None), "session_key", "") or "" if request else "",
    )


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")) or None


# ---------------------------------------------------------------- credenciales
def _slug(text):
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in text if c.isalnum() and not unicodedata.combining(c)).lower()


def ensure_username(user):
    """Usuario del sistema: se respeta el que ya tiene; si es un marcador (vacío o con puntos del
    nombre completo), se arma con la inicial del nombre y el apellido: «jtorres»."""
    User = get_user_model()
    current = user.username or ""
    if current and "." not in current and "@" not in current and len(current) <= 30:
        return current
    email_local = (user.email or "").split("@")[0].lower()
    base = email_local if email_local and email_local.isalnum() else (_slug(user.first_name)[:1] + _slug(user.last_name.split(" ")[0] if user.last_name else ""))
    base = base or "usuario"
    candidate, n = base, 1
    while User.objects.filter(username=candidate).exclude(pk=user.pk).exists():
        n += 1
        candidate = f"{base}{n}"
    user.username = candidate
    return candidate


def generate_password():
    """14 caracteres legibles en 3 bloques (≈ 68 bits de entropía), p. ej. «Kx7m-Qp4t-Wz9r»."""
    while True:
        blocks = ["".join(secrets.choice(READABLE) for _ in range(4)) for _ in range(3)]
        pwd = "-".join(blocks)
        if any(c.isdigit() for c in pwd) and any(c.isupper() for c in pwd) and any(c.islower() for c in pwd):
            return pwd


@transaction.atomic
def issue_credentials(user, actor, request=None, reason="Credenciales generadas"):
    """Genera usuario y contraseña temporal. La contraseña se muestra una sola vez al administrador;
    solo se guarda cifrada. El usuario deberá cambiarla al ingresar."""
    username = ensure_username(user)
    password = generate_password()
    user.set_password(password)
    user.must_change_password = True
    user.credentials_issued_at = timezone.now()
    _mark_verified(user)
    user.save()
    if not user.groups.exists():
        group = Group.objects.filter(name=DEFAULT_ROLE).first()
        if group:
            user.groups.add(group)
    _audit(actor, "issue_credentials", user, after={"username": username}, reason=reason, request=request)
    notify([user], kind="credenciales", title="Tus credenciales de acceso están listas",
           body="Al ingresar por primera vez el sistema te pedirá crear tu propia contraseña.", url=reverse("accounts:profile"), actor=actor)
    return username, password


def _mark_verified(user):
    """Un administrador revisó a la persona al darle acceso: deja de figurar «por verificar»."""
    user.is_active = True
    user.status = "active"
    user.status_as_of = timezone.localdate()
    user.source_verified = True


# ---------------------------------------------------------------- contraseñas
def can_change_own_password(user):
    return is_sgsi_admin(user) or user.must_change_password or user.password_changes == 0


@transaction.atomic
def change_own_password(user, new_password, request=None):
    validate_password(new_password, user=user)
    if not can_change_own_password(user):
        raise PermissionError("Para volver a cambiar la contraseña hay que enviar una solicitud.")
    forced = user.must_change_password
    user.set_password(new_password)
    user.must_change_password = False
    user.password_changes += 1
    user.password_changed_at = timezone.now()
    user.save(update_fields=["password", "must_change_password", "password_changes", "password_changed_at"])
    _audit(user, "change_password", user, after={"forzado": forced}, request=request)


@transaction.atomic
def request_password_change(user, reason, request=None):
    existing = user.password_requests.filter(status="pending").first()
    if existing:
        return existing, False
    req = PasswordChangeRequest.objects.create(user=user, reason=reason.strip()[:2000])
    _audit(user, "request_password_change", user, after={"solicitud": req.pk}, reason=reason, request=request)
    notify(sgsi_admins(), kind="solicitud_contrasena", title=f"{user.get_full_name() or user.username} solicita cambiar su contraseña",
           body=reason.strip()[:300], url=reverse("accounts:access_list") + "#solicitudes", actor=user)
    return req, True


@transaction.atomic
def resolve_password_request(req, actor, approve, note="", request=None):
    """Si se aprueba, se genera una contraseña temporal (se muestra una vez al administrador para que
    la entregue) y el usuario la cambia al ingresar."""
    if req.status != "pending":
        raise ValueError("La solicitud ya fue atendida.")
    req.status = "approved" if approve else "rejected"
    req.resolved_by = actor
    req.resolved_at = timezone.now()
    req.resolution_note = note.strip()[:2000]
    req.save()
    password = None
    if approve:
        _, password = issue_credentials(req.user, actor, request=request, reason="Solicitud de cambio de contraseña aprobada")
    else:
        _audit(actor, "reject_password_request", req.user, reason=note, request=request)
    notify([req.user], kind="solicitud_resuelta",
           title="Tu solicitud de cambio de contraseña fue " + ("aprobada" if approve else "rechazada"),
           body=("Recibirás una contraseña temporal; al ingresar crearás la tuya." if approve else note) or "",
           url=reverse("accounts:password_change"), actor=actor)
    return password


# ---------------------------------------------------------------- permisos por módulo
def _perm(ref):
    app_label, codename = ref.split(".", 1)
    return Permission.objects.filter(content_type__app_label=app_label, codename=codename).first()


def available_modules():
    """Módulos cuyo modelo existe en esta instalación."""
    out = []
    for key, label, models in MODULES:
        present = []
        for ref in models:
            app_label, model = ref.split(".")
            try:
                apps.get_model(app_label, model)
                present.append(ref)
            except LookupError:
                continue
        if present:
            out.append((key, label, present))
    return out


def module_perms(key, models, level):
    refs = []
    for ref in models:
        app_label, model = ref.split(".")
        refs.append(f"{app_label}.view_{model}")
        if level == "edit":
            refs += [f"{app_label}.add_{model}", f"{app_label}.change_{model}"]
    if level == "edit":
        refs += EXTRA_EDIT_PERMS.get(key, [])
    return [p for p in (_perm(r) for r in refs) if p]


def module_state(user):
    """Para cada módulo: si el usuario ve o edita (por rol o directo)."""
    rows = []
    for key, label, models in available_modules():
        view_codes = {f"{m.split('.')[0]}.view_{m.split('.')[1]}" for m in models}
        edit_codes = {f"{m.split('.')[0]}.change_{m.split('.')[1]}" for m in models}
        direct = {f"{p.content_type.app_label}.{p.codename}" for p in user.user_permissions.select_related("content_type")}
        group_perms = {f"{p.content_type.app_label}.{p.codename}" for p in Permission.objects.filter(group__user=user).select_related("content_type")}
        rows.append({
            "key": key, "label": label,
            "view_role": bool(view_codes & group_perms), "edit_role": bool(edit_codes & group_perms),
            "view": bool(view_codes & (direct | group_perms)), "edit": bool(edit_codes & (direct | group_perms)),
            "view_direct": bool(view_codes & direct), "edit_direct": bool(edit_codes & direct),
        })
    return rows


@transaction.atomic
def set_user_access(user, actor, *, roles, module_levels, active, request=None):
    """roles: nombres de grupo marcados. module_levels: {clave: "none" | "view" | "edit"} (permisos directos)."""
    before = {"roles": sorted(user.groups.values_list("name", flat=True)), "activo": user.is_active,
              "directos": sorted(f"{p.content_type.app_label}.{p.codename}" for p in user.user_permissions.select_related("content_type"))}
    if user == actor and ADMIN_ROLE in before["roles"] and ADMIN_ROLE not in roles:
        raise ValueError("No puede quitarse a sí mismo el rol de administrador.")
    if ADMIN_ROLE in before["roles"] and ADMIN_ROLE not in roles and sgsi_admins().exclude(pk=user.pk).count() == 0:
        raise ValueError("Debe quedar al menos un administrador del SGSI.")
    if user == actor and not active:
        raise ValueError("No puede desactivar su propia cuenta.")

    user.groups.set(Group.objects.filter(name__in=roles))
    managed = {p.pk for key, _, models in available_modules() for p in module_perms(key, models, "edit")}
    keep = [p for p in user.user_permissions.all() if p.pk not in managed]
    new = []
    for key, _, models in available_modules():
        level = module_levels.get(key, "none")
        if level in ("view", "edit"):
            new += module_perms(key, models, level)
    user.user_permissions.set(keep + new)
    user.is_active = active
    user.is_staff = ADMIN_ROLE in roles  # los administradores también entran al panel técnico
    if active:
        _mark_verified(user)
    user.save()
    if hasattr(user, "_sgsi_admin"):
        del user._sgsi_admin
    after = {"roles": sorted(roles), "activo": active,
             "directos": sorted(f"{p.content_type.app_label}.{p.codename}" for p in user.user_permissions.select_related("content_type"))}
    if before != after:
        _audit(actor, "set_access", user, before=before, after=after, request=request)
        notify([user], kind="permisos", title="Tus permisos en el sistema cambiaron",
               body="Revisa en tu perfil qué puedes ver y editar.", url=reverse("accounts:profile"), actor=actor)
    return before != after


def sync_admin_role():
    """El rol de administrador ve, crea y edita en todos los módulos del sistema (sin borrar)."""
    group, _ = Group.objects.get_or_create(name=ADMIN_ROLE)
    perms = Permission.objects.filter(content_type__app_label__in=[a.label for a in apps.get_app_configs() if a.name.startswith("apps.")])
    perms = perms.exclude(codename__startswith="delete_")
    group.permissions.add(*perms)
    return perms.count()
