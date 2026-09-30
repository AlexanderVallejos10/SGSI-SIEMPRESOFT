"""Pantallas del gobierno del SGSI."""

import datetime as dt

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.security import is_sgsi_admin, notify
from apps.accounts.views_access import admin_required
from apps.auditlog.services import register_audit_event

from .models import ManagementReview, ReviewDecision
from .services import (
    ACCEPTANCE_RULE,
    acceptance_rows,
    accesses_due,
    decide_acceptance,
    is_top_management,
    next_review_code,
    review_access,
    review_inputs,
)


def _date(value):
    try:
        return dt.date.fromisoformat(value) if value else None
    except ValueError:
        return None


# ---------------------------------------------------------------- revisión por la Dirección
@login_required
def review_list(request):
    return render(request, "governance/review_list.html", {
        "reviews": ManagementReview.objects.prefetch_related("decisions"),
        "can_edit": is_sgsi_admin(request.user),
        "today": timezone.localdate(),
    })


@admin_required
@require_POST
def review_create(request):
    when = _date(request.POST.get("review_date")) or timezone.localdate()
    previous = ManagementReview.objects.filter(status="approved").order_by("-review_date").first()
    review = ManagementReview.objects.create(
        code=next_review_code(when.year),
        title=request.POST.get("title", "").strip()[:200] or f"Revisión por la Dirección {when.year}",
        review_date=when, period_from=_date(request.POST.get("period_from")), period_to=_date(request.POST.get("period_to")),
        inputs=review_inputs(previous), inputs_at=timezone.now(), prepared_by=request.user,
    )
    register_audit_event(user=request.user, module="governance", action="create_review", entity="ManagementReview", entity_id=review.pk)
    messages.success(request, f"Revisión {review.code} creada con los datos actuales del sistema.")
    return redirect("governance:review_detail", pk=review.pk)


@login_required
def review_detail(request, pk):
    review = get_object_or_404(ManagementReview, pk=pk)
    can_edit = is_sgsi_admin(request.user) and not review.is_locked
    if request.method == "POST":
        if not can_edit and request.POST.get("action") != "decision_status":
            raise PermissionDenied
        _handle_review_post(request, review)
        return redirect("governance:review_detail", pk=review.pk)
    User = get_user_model()
    return render(request, "governance/review_detail.html", {
        "r": review, "i": review.inputs or {}, "can_edit": can_edit,
        "can_approve": not review.is_locked and is_top_management(request.user),
        "people": User.objects.filter(is_active=True).order_by("first_name", "last_name"),
        "print": request.GET.get("imprimir") == "1",
    })


def _handle_review_post(request, review):
    action = request.POST.get("action")
    if action == "texts":
        for field in ("title", "attendees", "internal_external_changes", "stakeholder_changes", "stakeholder_feedback",
                      "improvement_opportunities", "conclusions"):
            if field in request.POST:
                setattr(review, field, request.POST[field].strip())
        review.review_date = _date(request.POST.get("review_date")) or review.review_date
        review.save()
        messages.success(request, "Revisión guardada.")
    elif action == "refresh":
        previous = ManagementReview.objects.filter(status="approved").exclude(pk=review.pk).order_by("-review_date").first()
        review.inputs = review_inputs(previous)
        review.inputs_at = timezone.now()
        review.save(update_fields=["inputs", "inputs_at", "updated_at"])
        messages.success(request, "Datos del sistema actualizados.")
    elif action == "decision":
        text = request.POST.get("description", "").strip()
        if not text:
            messages.error(request, "Describa la decisión.")
            return
        responsible = get_user_model().objects.filter(pk=request.POST.get("responsible") or None).first()
        ReviewDecision.objects.create(review=review, kind=request.POST.get("kind", "mejora"), description=text,
                                      responsible=responsible, due_date=_date(request.POST.get("due_date")))
        messages.success(request, "Decisión agregada.")
    elif action == "decision_status":
        decision = get_object_or_404(ReviewDecision, pk=request.POST.get("decision"), review=review)
        if not (is_sgsi_admin(request.user) or decision.responsible_id == request.user.pk):
            raise PermissionDenied
        status = request.POST.get("status")
        if status in dict(ReviewDecision.STATUS):
            decision.status = status
            decision.closed_at = timezone.localdate() if status == "cumplida" else None
            decision.save(update_fields=["status", "closed_at"])
            messages.success(request, "Estado de la decisión actualizado.")
    elif action == "approve":
        if not is_top_management(request.user):
            raise PermissionDenied
        review.status = "approved"
        review.approved_by = request.user
        review.approved_at = timezone.now()
        review.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        url = reverse("governance:review_detail", args=[review.pk])
        for d in review.decisions.select_related("responsible"):
            if d.responsible:
                notify([d.responsible], kind="revision_direccion", title=f"Decisión de la {review.title} a su cargo",
                       body=d.description[:300], url=url, actor=request.user)
        register_audit_event(user=request.user, module="governance", action="approve_review", entity="ManagementReview", entity_id=review.pk)
        messages.success(request, "Revisión aprobada. Se avisó a los responsables de cada decisión.")


# ---------------------------------------------------------------- aceptación del riesgo residual
@login_required
def acceptance(request):
    from apps.risks.models import Risk

    if request.method == "POST":
        risk = get_object_or_404(Risk, pk=request.POST.get("risk"), is_active=True)
        decision = "rejected" if request.POST.get("decision") == "rejected" else "accepted"
        try:
            decide_acceptance(risk, request.user, decision, request.POST.get("justification", ""))
            messages.success(request, f"{risk.code}: decisión registrada.")
        except (PermissionError, ValueError) as exc:
            messages.error(request, str(exc))
        return redirect(f"{reverse('governance:acceptance')}#{risk.code}")
    rows = acceptance_rows(Risk.objects.filter(is_active=True).order_by("code"))
    show = request.GET.get("ver", "pendientes")
    if show == "pendientes":
        rows = [r for r in rows if not r["acceptance"]]
    return render(request, "governance/acceptance.html", {
        "rows": rows, "show": show, "rules": ACCEPTANCE_RULE,
        "stats": {"pending": sum(1 for r in acceptance_rows(Risk.objects.filter(is_active=True)) if not r["acceptance"])},
    })


# ---------------------------------------------------------------- revisión periódica de accesos
@admin_required
def access_review(request):
    from apps.accounts.models import SystemAccess

    if request.method == "POST":
        access = get_object_or_404(SystemAccess, pk=request.POST.get("access"))
        decision = request.POST.get("decision")
        if decision not in ("keep", "modify", "revoke"):
            messages.error(request, "Elija mantener, modificar o revocar.")
        elif decision != "keep" and len(request.POST.get("comments", "").strip()) < 5:
            messages.error(request, "Explique qué se modifica o por qué se revoca.")
        else:
            review_access(access, request.user, decision, request.POST.get("comments", ""))
            messages.success(request, "Revisión registrada.")
        return redirect("governance:access_review")
    due = list(accesses_due())
    groups = {}
    for a in due:
        groups.setdefault(a.user, []).append(a)
    q = request.GET.get("q", "").strip().lower()
    if q:
        groups = {u: items for u, items in groups.items() if q in (u.get_full_name() or u.username).lower()}
    from apps.accounts.models import AccessReview

    return render(request, "governance/access_review.html", {
        "groups": groups, "due": len(due),
        "done_90": AccessReview.objects.filter(reviewed_at__gte=timezone.localdate() - dt.timedelta(days=90)).count(),
        "q": q,
    })


# ---------------------------------------------------------------- Declaración de Aplicabilidad
@login_required
def soa(request):
    from apps.controls.models import Control
    from apps.documents.models import ManualReference
    from apps.risks.models import ANNEX_A_FRAMEWORK

    controls = (Control.objects.filter(framework__code=ANNEX_A_FRAMEWORK)
                .prefetch_related("risks", "risk_treatments__risk", "documents").select_related("owner").order_by("code"))
    rows = []
    for c in controls:
        risk_codes = sorted({r.code for r in c.risks.all() if r.is_active} | {t.risk.code for t in c.risk_treatments.all() if t.risk.is_active})
        rows.append({"c": c, "risks": risk_codes, "documents": [d.title for d in c.documents.all()]})

    def _count(field, value):
        return sum(1 for r in rows if getattr(r["c"], field) == value)

    return render(request, "governance/soa.html", {
        "rows": rows, "manual": ManualReference.objects.filter(is_current=True).first(), "today": timezone.localdate(),
        "stats": {"total": len(rows), "applicable": _count("applicability", "applicable"),
                  "not_applicable": _count("applicability", "not_applicable"), "pending": _count("applicability", "pending"),
                  "implemented": _count("implementation_status", "implemented"), "in_progress": _count("implementation_status", "in_progress")},
        "print": request.GET.get("imprimir") == "1",
    })
