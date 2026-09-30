"""Lógica del gobierno del SGSI.

- Entradas de la revisión por la Dirección (ISO/IEC 27001 9.3.2) tomadas de los datos reales del sistema.
- Riesgo residual con la misma tabla 5 × 4 de la metodología (risk_level) y aceptación por el propietario.
- Revisión periódica de accesos (A.5.18) sobre los accesos a sistemas registrados.
"""

import datetime as dt
import unicodedata

from django.db import transaction
from django.utils import timezone

from apps.auditlog.services import register_audit_event
from apps.traceability.services import risk_level

LEVEL_ORDER = {"Muy bajo": 1, "Bajo": 2, "Medio": 3, "Alto": 4, "Muy alto": 5}

# Criterio de aceptación del riesgo residual (ISO/IEC 27005 6.3). Propuesta a confirmar en la
# metodología de gestión de riesgos V0.10: quién puede aceptar cada nivel.
ACCEPTANCE_RULE = {
    "Muy bajo": ("owner", "Aceptable: lo confirma el propietario del riesgo."),
    "Bajo": ("owner", "Aceptable: lo confirma el propietario del riesgo."),
    "Medio": ("owner", "Lo acepta el propietario del riesgo, con justificación."),
    "Alto": ("top", "Solo lo acepta el Gerente General, con justificación."),
    "Muy alto": ("top", "Solo lo acepta el Gerente General, con justificación."),
}
REVIEW_EVERY_DAYS = 90  # revisión trimestral de accesos


def _norm(text):
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def is_top_management(user):
    """Gerente General (por su puesto vigente en el organigrama) o superusuario técnico."""
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    from apps.organization.models import PositionAssignment

    titles = PositionAssignment.objects.filter(user=user, end_date__isnull=True).values_list("position__title", flat=True)
    return any("gerente general" in _norm(t) for t in titles)


# ---------------------------------------------------------------- riesgo residual y aceptación
def residual_for(risk):
    """(probabilidad, consecuencia, nivel) residual: del tratamiento más reciente que lo tenga;
    si no, de la última valoración; si no hay, (None, None, "")."""
    treatments = sorted((t for t in risk.treatments.all() if t.residual_probability and t.residual_impact),
                        key=lambda t: (t.updated_at or t.created_at), reverse=True)
    if treatments:
        t = treatments[0]
        return t.residual_probability, t.residual_impact, risk_level(t.residual_probability, t.residual_impact)
    latest = next(iter(risk.assessments.all()), None)
    if latest and latest.residual_probability and latest.residual_impact:
        return latest.residual_probability, latest.residual_impact, risk_level(latest.residual_probability, latest.residual_impact)
    return None, None, ""


def inherent_for(risk):
    latest = next(iter(risk.assessments.all()), None)
    return (latest.probability, latest.impact, risk_level(latest.probability, latest.impact)) if latest else (None, None, "")


def can_accept(user, risk, level):
    from apps.accounts.security import is_sgsi_admin

    who, _ = ACCEPTANCE_RULE.get(level, ("top", ""))
    if who == "top":
        return is_top_management(user)
    if is_top_management(user) or is_sgsi_admin(user):
        return True
    if risk.owner_id == user.pk:
        return True
    if risk.owner_position_id:
        from apps.organization.models import PositionAssignment

        return PositionAssignment.objects.filter(user=user, position_id=risk.owner_position_id, end_date__isnull=True).exists()
    return False


def acceptance_rows(queryset):
    rows = []
    for risk in queryset.prefetch_related("assessments", "treatments", "acceptances").select_related("owner", "owner_position"):
        ip, ic, inherent = inherent_for(risk)
        rp, rc, residual = residual_for(risk)
        current = next((a for a in risk.acceptances.all() if a.is_current), None)
        level_for_rule = residual or inherent
        valid = bool(current and current.residual_level == residual and current.inherent_level == inherent)
        rows.append({
            "risk": risk, "inherent": inherent, "residual": residual, "residual_pc": (rp, rc),
            "level_for_rule": level_for_rule, "rule": ACCEPTANCE_RULE.get(level_for_rule, ("", ""))[1],
            "acceptance": current if valid else None, "outdated": bool(current and not valid),
        })
    return rows


@transaction.atomic
def decide_acceptance(risk, user, decision, justification):
    ip, ic, inherent = inherent_for(risk)
    rp, rc, residual = residual_for(risk)
    level = residual or inherent
    if not can_accept(user, risk, level):
        raise PermissionError(ACCEPTANCE_RULE.get(level, ("", "No tiene permiso para decidir sobre este riesgo."))[1])
    if len((justification or "").strip()) < 10:
        raise ValueError("Escriba la justificación de la decisión.")
    risk.acceptances.filter(is_current=True).update(is_current=False)
    from .models import RiskAcceptance

    acc = RiskAcceptance.objects.create(risk=risk, inherent_level=inherent, residual_probability=rp, residual_impact=rc,
                                        residual_level=residual, decision=decision, justification=justification.strip(), decided_by=user)
    register_audit_event(user=user, module="risks", action=f"risk_{decision}", entity="Risk", entity_id=risk.pk,
                         after={"codigo": risk.code, "residual": residual or "sin calcular", "inherente": inherent}, reason=justification)
    return acc


# ---------------------------------------------------------------- revisión por la Dirección (9.3.2)
def review_inputs(previous=None):
    """Entradas de la revisión tomadas del sistema. Se guardan tal como estaban ese día."""
    from apps.dashboard_live import overview
    from apps.dashboard_live.selectors import build_dashboard_context
    from apps.risks.models import Risk, RiskTreatment

    data = {"generated_at": timezone.now().isoformat()}
    # a) estado de las acciones de revisiones anteriores
    if previous:
        data["a_previous"] = {
            "code": previous.code,
            "decisions": [{"description": d.description, "status": d.get_status_display(),
                           "responsible": (d.responsible.get_full_name() if d.responsible else ""),
                           "due": d.due_date.isoformat() if d.due_date else ""} for d in previous.decisions.all()],
        }
    # d) desempeño: no conformidades y acciones correctivas, seguimiento y medición, auditorías, objetivos
    corr = overview.corrective()
    audits = overview.audits()
    data["d1_corrective"] = {"total": corr.get("total", 0), "done": corr.get("done", 0), "pending": corr.get("pending", 0), "pct": corr.get("pct", 0)}
    data["d3_audits"] = {"audits": audits.get("audits", 0), "findings": audits.get("findings", 0), "open": audits.get("open", 0),
                         "closed": audits.get("closed", 0), "last": audits.get("last")}
    ctx = build_dashboard_context()
    if ctx.get("dataset"):
        data["d2_metrics"] = {
            "source": ctx["dataset"].original_name, "yes": ctx["sgsi_yes"], "total": ctx["sgsi_total"],
            "rows": [{"id": r["obj"].metric_id, "description": r["obj"].description, "value": r["display"], "target": r["obj"].indicator,
                      "ok": r["compliance"] == "SI"} for r in ctx["sgsi_rows"]],
        }
        data["d4_objectives"] = {
            "yes": ctx["oesi_yes"], "total": ctx["oesi_total"],
            "rows": [{"id": r["obj"].metric_id, "description": r["obj"].description, "value": r["display"], "target": r["obj"].indicator,
                      "ok": r["compliance"] == "SI"} for r in ctx["oesi_rows"]],
        }
    incidents = overview.incidents()
    data["incidents"] = {"total": incidents.get("total", 0), "open": incidents.get("open", 0),
                         "last_year": incidents.get("last_year"), "last_count": incidents.get("last_count", 0)}
    # f) evaluación de riesgos y estado del plan de tratamiento
    risk_summary = overview.risks()
    rows = acceptance_rows(Risk.objects.filter(is_active=True))
    treatments = RiskTreatment.objects.filter(risk__is_active=True)
    data["f_risks"] = {
        "total": risk_summary.get("total", 0), "high": risk_summary.get("high", 0),
        "levels": [{"name": lv["name"], "count": lv["count"]} for lv in risk_summary.get("levels", [])],
        "treatments": treatments.count(), "treatments_closed": treatments.filter(closed_date__isnull=False).count(),
        "residual_calculated": sum(1 for r in rows if r["residual"]),
        "accepted": sum(1 for r in rows if r["acceptance"] and r["acceptance"].decision == "accepted"),
    }
    return data


def next_review_code(year):
    from .models import ManagementReview

    n = ManagementReview.objects.filter(code__startswith=f"RD-{year}-").count() + 1
    return f"RD-{year}-{n:02d}"


# ---------------------------------------------------------------- revisión periódica de accesos (A.5.18)
def accesses_due(today=None):
    from apps.accounts.models import SystemAccess

    today = today or timezone.localdate()
    return (SystemAccess.objects.filter(status__in=("active", "unknown"))
            .exclude(next_review_at__gt=today)
            .select_related("user", "system").order_by("user__first_name", "user__last_name", "system__name"))


@transaction.atomic
def review_access(access, reviewer, decision, comments=""):
    from apps.accounts.models import AccessReview

    today = timezone.localdate()
    seq = AccessReview.objects.filter(business_code__startswith=f"RA-{today:%Y%m%d}-").count() + 1
    nxt = today + dt.timedelta(days=REVIEW_EVERY_DAYS)
    review = AccessReview.objects.create(
        business_code=f"RA-{today:%Y%m%d}-{seq:03d}", access=access, reviewer=reviewer, reviewed_at=today,
        decision=decision, comments=comments.strip(), next_review_at=nxt if decision != "revoke" else None,
        source_reference="Revisión periódica de accesos en el sistema", source_verified=True,
        created_by=reviewer, updated_by=reviewer,
    )
    access.last_review_at = today
    access.next_review_at = nxt if decision != "revoke" else None
    fields = ["last_review_at", "next_review_at", "updated_by"]
    access.updated_by = reviewer
    if decision == "revoke":
        access.status = "revoked"
        access.revoked_at = timezone.now()
        fields += ["status", "revoked_at"]
    elif access.status == "unknown":
        access.status = "active"
        fields.append("status")
    access.save(update_fields=fields)
    register_audit_event(user=reviewer, module="accounts", action=f"access_review_{decision}", entity="SystemAccess",
                         entity_id=access.pk, after={"revision": review.business_code}, reason=comments)
    return review
