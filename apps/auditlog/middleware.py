from django.conf import settings

from .context import (
    AuditRequestContext,
    reset_audit_context,
    set_audit_context,
)


def get_client_ip(request):
    """
    Obtiene la IP del cliente.

    X-Forwarded-For solo se utiliza cuando se configure
    explícitamente un proxy de confianza.
    """

    if getattr(settings, "AUDIT_TRUST_X_FORWARDED_FOR", False):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR")


class AuditContextMiddleware:
    """
    Mantiene usuario, IP y sesión disponibles durante
    toda la petición HTTP.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)

        session = getattr(request, "session", None)

        session_key = ""
        if session is not None:
            session_key = session.session_key or ""

        context = AuditRequestContext(
            user=user,
            ip_address=get_client_ip(request),
            session_key=session_key,
        )

        token = set_audit_context(context)

        try:
            return self.get_response(request)
        finally:
            reset_audit_context(token)