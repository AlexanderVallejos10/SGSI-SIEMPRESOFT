"""Registro de ingresos, salidas e intentos fallidos."""

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.utils import timezone

from apps.auditlog.services import register_audit_event

from .models import LoginAttempt, UserSession
from .security import client_ip


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    if request is None:
        return
    if not request.session.session_key:
        request.session.save()
    now = timezone.now()
    request.session["activity_ts"] = now.timestamp()
    request.session["presence_ts"] = now.timestamp()
    UserSession.objects.create(
        user=user, session_key=request.session.session_key, started_at=now, last_seen_at=now,
        ip_address=client_ip(request), user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
    )
    type(user).objects.filter(pk=user.pk).update(last_seen_at=now)
    LoginAttempt.objects.create(username=user.get_username(), ip_address=client_ip(request), success=True)
    register_audit_event(user=user, module="accounts", action="login", entity="User", entity_id=user.pk,
                         ip_address=client_ip(request), session_key=request.session.session_key or "")


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    if request is None or user is None:
        return
    key = request.session.session_key
    UserSession.objects.filter(session_key=key, ended_at__isnull=True).update(ended_at=timezone.now(), ended_reason="logout")
    register_audit_event(user=user, module="accounts", action="logout", entity="User", entity_id=user.pk,
                         ip_address=client_ip(request), session_key=key or "")


@receiver(user_login_failed)
def on_failed(sender, credentials, request=None, **kwargs):
    username = (credentials or {}).get("username", "")[:150]
    ip = client_ip(request) if request else None
    LoginAttempt.objects.create(username=username, ip_address=ip, success=False)
    register_audit_event(user=None, module="accounts", action="login_failed", entity="User", entity_id=username or "-",
                         result="failure", ip_address=ip)
