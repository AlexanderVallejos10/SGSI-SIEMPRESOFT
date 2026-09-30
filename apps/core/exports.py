"""Respuesta de descarga de Excel que deja constancia en la auditoría (quién exportó qué y cuándo)."""

from django.http import HttpResponse
from django.utils import timezone

from apps.auditlog.services import register_audit_event

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def excel_download(request, content, filename, *, module, entity):
    from apps.accounts.security import client_ip

    register_audit_event(user=request.user, module=module, action="export_excel", entity=entity, entity_id=filename,
                         ip_address=client_ip(request), session_key=request.session.session_key or "")
    response = HttpResponse(content, content_type=XLSX)
    stamp = timezone.localdate().strftime("%Y-%m-%d")
    response["Content-Disposition"] = f'attachment; filename="{filename}_{stamp}.xlsx"'
    response["Cache-Control"] = "no-store"
    return response
