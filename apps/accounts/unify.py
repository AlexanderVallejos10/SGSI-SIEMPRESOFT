"""Unificación de personas duplicadas: un código, una persona, una cuenta.

Dos cuentas son la misma persona si comparten correo, o el primer nombre y al menos un apellido
(«Milton Guevara» = «Milton Guevara Santisteban»). La cuenta que queda es la que tiene más uso real;
todo lo que apuntaba a la duplicada (puestos, activos, movimientos, riesgos, auditoría, sesiones, roles)
pasa a ella y la duplicada queda desactivada como historial (nunca se borra). Los casos dudosos no se tocan: se informan."""

import re
import unicodedata

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.auditlog.services import register_audit_event
from apps.core.merging import MERGED_SUFFIX

KEEP_HISTORY = {"auditlog.auditlog"}

PARTICLES = {"de", "del", "la", "las", "los", "y", "ing", "lic", "dr", "dra", "mg"}


def tokens(text):
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return [t for t in re.split(r"[^a-z]+", text) if t and t not in PARTICLES]


def _identity(user):
    first = tokens(user.first_name)
    last = tokens(user.last_name)
    if not first and not last:  # nombre completo guardado en un solo campo
        full = tokens(user.get_full_name() or "")
        first, last = full[:1], full[1:]
    return (first[:1] or [""])[0], set(last)


def same_person(a, b):
    if a.email and b.email and a.email.strip().lower() == b.email.strip().lower():
        return True
    fa, la = _identity(a)
    fb, lb = _identity(b)
    return bool(fa) and fa == fb and bool(la & lb)


def score(user):
    from .security import ADMIN_ROLE

    return (
        (8 if user.has_usable_password() else 0) + (4 if user.last_login else 0)
        + (4 if user.is_superuser or user.groups.filter(name=ADMIN_ROLE).exists() else 0)
        + (2 if user.email else 0) + (2 if user.photo else 0)
        + (1 if user.business_code and not user.business_code.startswith("COL-") else 0),
        -user.date_joined.timestamp(),
    )


def duplicate_groups():
    """Grupos de cuentas que son la misma persona. Devuelve [(canónica, [duplicadas], dudoso)]."""
    User = get_user_model()
    users = list(User.objects.exclude(username__endswith=MERGED_SUFFIX).prefetch_related("groups"))
    parent = {u.pk: u.pk for u in users}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    by_first = {}
    for u in users:
        by_first.setdefault(_identity(u)[0], []).append(u)
    for bucket in list(by_first.values()) + [[u for u in users if u.email]]:
        for i, a in enumerate(bucket):
            for b in bucket[i + 1:]:
                if same_person(a, b):
                    parent[find(a.pk)] = find(b.pk)
    groups = {}
    for u in users:
        groups.setdefault(find(u.pk), []).append(u)
    out = []
    for members in groups.values():
        if len(members) < 2:
            continue
        members.sort(key=score, reverse=True)
        keep, dups = members[0], members[1:]
        emails = {m.email.strip().lower() for m in members if m.email and m.has_usable_password()}
        doubtful = sum(1 for m in members if m.has_usable_password()) > 1 and len(emails) > 1
        out.append((keep, dups, doubtful))
    return out


def _move_relations(dup, keep):
    """Pasa a «keep» todo lo que apunta a «dup». Devuelve las relaciones que no se pudieron mover."""
    User = get_user_model()
    failed = []
    for rel in User._meta.related_objects:
        model = rel.related_model
        if model._meta.label_lower in KEEP_HISTORY:
            continue
        if rel.many_to_many:
            accessor = rel.get_accessor_name()
            for obj in getattr(dup, accessor).all():
                getattr(obj, rel.field.name).add(keep)
            continue
        if not getattr(rel.field, "concrete", False):
            continue
        field = rel.field.name
        qs = model._base_manager.filter(**{field: dup})
        try:
            with transaction.atomic():
                qs.update(**{field: keep})
        except IntegrityError:
            for obj in qs:  # fila por fila: la que choca con una única (p. ej. un puesto vigente) se cierra primero
                try:
                    with transaction.atomic():
                        if hasattr(obj, "end_date") and getattr(obj, "end_date") is None:
                            obj.end_date = timezone.localdate()
                        setattr(obj, field, keep)
                        obj.save()
                except IntegrityError:
                    failed.append(f"{model._meta.verbose_name}: {obj.pk}")
    # relaciones M2M declaradas en el propio usuario (roles y permisos)
    keep.groups.add(*dup.groups.all())
    keep.user_permissions.add(*dup.user_permissions.all())
    return failed


def _merge_fields(dup, keep):
    for field in ("email", "first_name", "area", "position", "document_number", "employment_start", "employment_end", "manager_id"):
        if not getattr(keep, field, None) and getattr(dup, field, None):
            setattr(keep, field, getattr(dup, field))
    # apellido más completo («Guevara» → «Guevara Santisteban») si contiene al actual
    if dup.last_name and len(dup.last_name) > len(keep.last_name or "") and set(tokens(keep.last_name)) <= set(tokens(dup.last_name)):
        keep.last_name = dup.last_name
    if not keep.photo and dup.photo:
        keep.photo = dup.photo.name
    if dup.is_active and not keep.is_active:
        keep.is_active = True


def _retire_user(dup):
    from .models import UserStatus

    dup.is_active = False
    dup.status = UserStatus.INACTIVE
    dup.status_as_of = timezone.localdate()
    if not dup.username.endswith(MERGED_SUFFIX):
        dup.username = f"{dup.username[:150 - len(MERGED_SUFFIX)]}{MERGED_SUFFIX}"
    if dup.business_code and not dup.business_code.endswith("-DUP"):
        dup.business_code = f"{dup.business_code[:26]}-DUP"
    dup.set_unusable_password()
    dup.save()


@transaction.atomic
def merge(keep, dups, actor=None):
    report = []
    for dup in dups:
        failed = _move_relations(dup, keep)
        _merge_fields(dup, keep)
        keep.save()
        register_audit_event(user=actor, module="accounts", action="merge_user", entity="User", entity_id=keep.pk,
                             before={"duplicada": str(dup.pk), "codigo": dup.business_code, "usuario": dup.username},
                             after={"codigo": keep.business_code, "usuario": keep.username},
                             reason="Unificación de personas duplicadas")
        code = dup.business_code
        _retire_user(dup)
        if failed:
            report.append(f"{dup.username}: desactivada (no se pudo mover: {', '.join(failed)})")
        else:
            report.append(f"{code}: unificada (la cuenta duplicada queda desactivada)")
    return report


# ---------------------------------------------------------------- activos con códigos equivalentes
def asset_key(code):
    """SS1-CPU-012, SS1-CPU-12 y ss1 cpu 12 son el mismo código."""
    parts = re.findall(r"[A-Za-z]+|\d+", code or "")
    return "-".join(p.upper() if p.isalpha() else str(int(p)) for p in parts)


def duplicate_assets():
    from apps.assets.models import Asset

    groups = {}
    for asset in Asset.objects.exclude(code__endswith=MERGED_SUFFIX).order_by("created_at"):
        groups.setdefault(asset_key(asset.code), []).append(asset)
    out = []
    for members in groups.values():
        if len(members) > 1:
            members.sort(key=lambda a: (a.movements.count() + a.maintenances.count(), bool(a.custodian_id)), reverse=True)
            out.append((members[0], members[1:]))
    return out


@transaction.atomic
def merge_assets(keep, dups, actor=None):
    from apps.assets.models import Asset

    for dup in dups:
        for rel in Asset._meta.related_objects:
            if rel.many_to_many or not getattr(rel.field, "concrete", False):
                continue
            rel.related_model._base_manager.filter(**{rel.field.name: dup}).update(**{rel.field.name: keep})
        for field in ("custodian_id", "hostname", "model", "location", "area", "serial"):
            if hasattr(keep, field) and not getattr(keep, field) and getattr(dup, field, None):
                setattr(keep, field, getattr(dup, field))
        keep.save()
        register_audit_event(user=actor, module="assets", action="merge_asset", entity="Asset", entity_id=keep.pk,
                             before={"duplicado": dup.code}, after={"codigo": keep.code}, reason="Unificación de activos duplicados")
        dup.code = f"{dup.code[:50 - len(MERGED_SUFFIX)]}{MERGED_SUFFIX}"
        dup.status = "retired"
        dup.custodian = None
        dup.save()
