from .models import AuditLog


def register_audit_event(*, user, module, action, entity, entity_id, before=None, after=None, result="success", reason="", ip_address=None, session_key=""):
    return AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        module=module,
        action=action,
        entity=entity,
        entity_id=str(entity_id),
        before=before or {},
        after=after or {},
        result=result,
        reason=reason,
        ip_address=ip_address,
        session_key=session_key,
    )
