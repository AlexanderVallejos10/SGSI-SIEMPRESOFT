from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AuditRequestContext:
    user: Any = None
    ip_address: str | None = None
    session_key: str = ""


_current_audit_context = ContextVar(
    "current_audit_context",
    default=AuditRequestContext(),
)


def set_audit_context(context: AuditRequestContext):
    return _current_audit_context.set(context)


def get_audit_context() -> AuditRequestContext:
    return _current_audit_context.get()


def reset_audit_context(token):
    _current_audit_context.reset(token)