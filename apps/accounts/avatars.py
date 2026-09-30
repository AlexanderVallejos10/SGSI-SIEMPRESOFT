"""Fotos de perfil: validación por contenido, recorte cuadrado y registro en la auditoría."""

import io
import uuid

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils.html import escape, format_html

from apps.auditlog.services import register_audit_event

MAX_BYTES = 5 * 1024 * 1024
SIGNATURES = ((b"\xff\xd8\xff", "jpg"), (b"\x89PNG\r\n\x1a\n", "png"))


def _kind(head):
    for magic, ext in SIGNATURES:
        if head.startswith(magic):
            return ext
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


def process(uploaded):
    """Devuelve (bytes, extensión). Con Pillow: se reencodifica en JPEG 512×512 y se quitan los metadatos
    (GPS, cámara); cualquier contenido extraño dentro del archivo se descarta. Sin Pillow: se valida el tipo."""
    data = uploaded.read()
    if len(data) > MAX_BYTES:
        raise ValidationError("La foto supera los 5 MB.")
    ext = _kind(data[:16])
    if not ext:
        raise ValidationError("Use una foto JPG, PNG o WebP.")
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return data, ext
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img).convert("RGB")
    except Exception as exc:
        raise ValidationError("El archivo no es una imagen válida.") from exc
    img = ImageOps.fit(img, (512, 512), method=Image.LANCZOS, centering=(0.5, 0.4))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=88, optimize=True, progressive=True)
    return out.getvalue(), "jpg"


def save_avatar(user, uploaded, actor, request=None):
    data, ext = process(uploaded)
    old = user.photo.name if user.photo else ""
    user.photo.save(f"{uuid.uuid4().hex}.{ext}", ContentFile(data), save=True)
    if old:
        user.photo.storage.delete(old)
    _audit(user, actor, "change_photo", request)
    if actor is not None and actor.pk != user.pk:
        from .security import notify
        notify([user], kind="foto", title="Tu foto de perfil cambió", actor=actor)


def remove_avatar(user, actor, request=None):
    if user.photo:
        user.photo.storage.delete(user.photo.name)
        user.photo = ""
        user.save(update_fields=["photo"])
        _audit(user, actor, "remove_photo", request)


def _audit(user, actor, action, request):
    from .security import client_ip

    register_audit_event(user=actor, module="accounts", action=action, entity="User", entity_id=user.pk,
                         ip_address=client_ip(request) if request else None,
                         session_key=(request.session.session_key or "") if request else "")


def initials(user):
    first = (user.first_name or "").strip()[:1]
    last = (user.last_name or "").strip()[:1]
    return (first + last).upper() or (user.username or "?")[:1].upper()


def avatar_html(user, size=""):
    cls = f"ac-avatar{' is-' + size if size else ''}"
    name = user.get_full_name() or user.username
    if user.photo:
        return format_html('<span class="{} has-photo"><img src="{}" alt="" loading="lazy" decoding="async"></span>', cls, user.photo.url)
    return format_html('<span class="{}" aria-hidden="true">{}</span>', cls, initials(user)) if name else ""
