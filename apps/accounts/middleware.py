"""Control de acceso en cada solicitud: cierre por inactividad, presencia y cambio obligatorio de contraseña."""

from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from .models import UserSession
from .presence import idle_limit, touch

# Rutas que se pueden usar aunque la contraseña esté pendiente de cambio.
ALLOWED_WHILE_PENDING = ("/static/", "/cuenta/contrasena/", "/salir/", "/api/pulso/", "/ingresar/")


class AccessControlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            now = timezone.now().timestamp()
            last = request.session.get("activity_ts")
            is_pulse = request.path.startswith("/api/pulso/")
            if last and now - last > idle_limit().total_seconds():
                key = request.session.session_key
                UserSession.objects.filter(session_key=key, ended_at__isnull=True).update(ended_at=timezone.now(), ended_reason="inactividad")
                logout(request)
                if is_pulse:
                    from django.http import JsonResponse
                    return JsonResponse({"logged_out": True, "login": reverse("accounts:login")}, status=401)
                messages.info(request, "La sesión se cerró por inactividad. Vuelva a ingresar.")
                return redirect(f"{reverse('accounts:login')}?next={request.get_full_path()}")
            if not is_pulse:  # el pulso automático no cuenta como actividad del usuario
                request.session["activity_ts"] = now
            touch(request)
            if user.must_change_password and not request.path.startswith(ALLOWED_WHILE_PENDING):
                return redirect("accounts:password_change")
        return self.get_response(request)
