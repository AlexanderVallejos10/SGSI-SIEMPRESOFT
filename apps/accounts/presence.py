"""Presencia y tiempo de conexión.

La última actividad se guarda como máximo una vez por minuto por sesión (no en cada clic), y la
página consulta /api/pulso/ cada 25 s mientras está abierta. Se considera «conectado» a quien tuvo
actividad en los últimos 2 minutos y no cerró sesión."""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import F, Sum
from django.utils import timezone

from .models import UserSession

ONLINE_WINDOW = timedelta(seconds=120)
TOUCH_EVERY = 60  # segundos


def idle_limit():
    return timedelta(minutes=getattr(settings, "SGSI_IDLE_MINUTES", 30))


def touch(request, force=False):
    """Marca actividad del usuario y de su sesión (con límite de una escritura por minuto)."""
    now = timezone.now()
    last = request.session.get("presence_ts", 0)
    if not force and now.timestamp() - last < TOUCH_EVERY:
        return
    request.session["presence_ts"] = now.timestamp()
    get_user_model().objects.filter(pk=request.user.pk).update(last_seen_at=now)
    key = request.session.session_key
    if key:
        updated = UserSession.objects.filter(session_key=key, ended_at__isnull=True).update(last_seen_at=now)
        if not updated:  # sesión anterior a este registro (p. ej. tras actualizar el sistema)
            UserSession.objects.create(user=request.user, session_key=key, started_at=now, last_seen_at=now)


def online_users():
    since = timezone.now() - ONLINE_WINDOW
    User = get_user_model()
    open_sessions = UserSession.objects.filter(ended_at__isnull=True, last_seen_at__gte=since)
    starts = {}
    for user_id, started in open_sessions.values_list("user_id", "started_at"):
        starts[user_id] = min(started, starts.get(user_id, started))
    users = list(User.objects.filter(pk__in=starts.keys(), is_active=True).order_by("first_name", "last_name"))
    for u in users:
        u.online_since = starts[u.pk]
    return users


def close_stale_sessions():
    """Cierra en el registro las sesiones que quedaron abiertas (navegador cerrado sin salir)."""
    limit = timezone.now() - idle_limit()
    return UserSession.objects.filter(ended_at__isnull=True, last_seen_at__lt=limit).update(
        ended_at=F("last_seen_at"), ended_reason="inactividad")


def connected_time(user, days=30):
    """Tiempo total conectado en los últimos N días."""
    since = timezone.now() - timedelta(days=days)
    total = timedelta()
    for s in UserSession.objects.filter(user=user, started_at__gte=since).only("started_at", "last_seen_at", "ended_at"):
        total += (s.ended_at or s.last_seen_at) - s.started_at
    return total


def human(delta):
    minutes = int(delta.total_seconds() // 60)
    if minutes < 1:
        return "menos de 1 min"
    hours, minutes = divmod(minutes, 60)
    if hours >= 24:
        days, hours = divmod(hours, 24)
        return f"{days} d {hours} h"
    return f"{hours} h {minutes:02d} min" if hours else f"{minutes} min"
