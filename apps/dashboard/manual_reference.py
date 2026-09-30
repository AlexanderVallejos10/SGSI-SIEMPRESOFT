"""Cambio de la versión del Manual del SGSI (solo administradores del SGSI)."""

import datetime

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.accounts.security import is_sgsi_admin, notify, sgsi_admins
from apps.auditlog.services import register_audit_event
from apps.documents.models import ManualReference


def manual_history(limit=10):
    return list(ManualReference.objects.select_related("changed_by")[:limit])


@require_POST
def update_manual_reference(request):
    if not is_sgsi_admin(request.user):
        raise PermissionDenied
    back = request.POST.get("next", "/")
    if not url_has_allowed_host_and_scheme(back, allowed_hosts={request.get_host()}):
        back = "/"
    version = request.POST.get("version", "").strip()
    note = request.POST.get("change_note", "").strip()
    if not version or not note:
        messages.error(request, "Indique la versión y qué cambió respecto a la anterior.")
        return redirect(back)
    status = request.POST.get("status", "Borrador")
    if status not in dict(ManualReference.STATUS):
        status = "Borrador"
    try:
        issue_date = datetime.date.fromisoformat(request.POST.get("issue_date", "")) if request.POST.get("issue_date") else None
    except ValueError:
        issue_date = None
    with transaction.atomic():
        previous = ManualReference.objects.select_for_update().filter(is_current=True).first()
        if previous:
            previous.is_current = False
            previous.save(update_fields=["is_current"])
        ref = ManualReference.objects.create(
            title=request.POST.get("title", "").strip()[:200] or (previous.title if previous else ManualReference._meta.get_field("title").default),
            version=version[:20], status=status, issue_date=issue_date,
            prepared_by=request.POST.get("prepared_by", "").strip()[:120], approved_by=request.POST.get("approved_by", "").strip()[:120],
            change_note=note, is_current=True, changed_by=request.user,
        )
        register_audit_event(user=request.user, module="documents", action="manual_version", entity="ManualReference", entity_id=ref.pk,
                             before={"version": previous.version, "estado": previous.status} if previous else {},
                             after={"version": ref.version, "estado": ref.status}, reason=note)
        notify(sgsi_admins().exclude(pk=request.user.pk), kind="manual",
               title=f"El Manual del SGSI pasó a la versión {ref.version} ({ref.status.lower()})", body=note[:300], url=back, actor=request.user)
    messages.success(request, f"Manual del SGSI actualizado a la versión {ref.version}.")
    return redirect(back)
