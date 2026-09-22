from decimal import Decimal

from django.urls import reverse

from .logic import compliance, factor_summary, relation_score
from .models import DashboardDataset, MatrixType


def current_dataset():
    return DashboardDataset.objects.filter(is_current=True).first()


def metric_display(metric):
    if metric.current_value is None:
        return metric.current_text or "—"
    value = metric.current_value
    if value == value.to_integral():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def build_dashboard_context():
    dataset = current_dataset()
    if dataset is None:
        return {"dataset": None}

    sgsi_metrics = list(dataset.sgsi_metrics.select_related("responsible_position").order_by("metric_id"))
    oesi_metrics = list(dataset.oesi_metrics.select_related("responsible_position").order_by("metric_id"))
    strategic = list(dataset.strategic_objectives.all())
    security = list(dataset.security_objectives.all())
    oee_alignments = list(dataset.oee_osi_alignments.select_related("strategic_objective", "security_objective"))
    requirements = list(dataset.stakeholder_requirements.all())
    req_alignments = list(dataset.requirement_osi_alignments.select_related("requirement", "security_objective"))
    factors = list(dataset.strategic_factors.all())

    mefi = factor_summary(factors, MatrixType.MEFI)
    mefe = factor_summary(factors, MatrixType.MEFE)

    oee_scores = {obj.code: relation_score(oee_alignments, obj) for obj in security}
    req_scores = {obj.code: relation_score(req_alignments, obj) for obj in security}

    oee_obtained = sum(oee_scores.values())
    oee_expected = len(security) * 7
    req_obtained = sum(req_scores.values())
    req_expected = len(security) * 17

    oee_pct = Decimal(oee_obtained) * Decimal("100") / Decimal(oee_expected or 1)
    req_pct = Decimal(req_obtained) * Decimal("100") / Decimal(req_expected or 1)

    sgsi_rows = []
    for metric in sgsi_metrics:
        effective = metric.current_value
        if metric.metric_id == 1:
            effective = oee_pct
        elif metric.metric_id == 2:
            effective = req_pct
        calc = compliance(metric.indicator, effective)
        sgsi_rows.append({
            "obj": metric,
            "effective": effective,
            "display": (
                f"{effective:.2f}".rstrip("0").rstrip(".")
                if effective is not None
                else (metric.current_text or "—")
            ),
            "compliance": calc,
            "source_mismatch": bool(metric.source_compliance) and bool(calc) and metric.source_compliance.strip().upper() != calc,
            "edit_url": reverse("dashboard_live:edit_sgsi_metric", args=[metric.pk]),
        })

    oesi_rows = []
    for metric in oesi_metrics:
        calc = compliance(metric.indicator, metric.current_value)
        oesi_rows.append({
            "obj": metric,
            "display": metric_display(metric),
            "compliance": calc,
            "source_mismatch": bool(metric.source_compliance) and bool(calc) and metric.source_compliance.strip().upper() != calc,
            "edit_url": reverse("dashboard_live:edit_oesi_metric", args=[metric.pk]),
        })

    sgsi_yes = sum(1 for row in sgsi_rows if row["compliance"] == "SI")
    oesi_yes = sum(1 for row in oesi_rows if row["compliance"] == "SI")

    warnings = []
    if mefi["weight_warning"]:
        warnings.append({
            "title": "Pesos MEFI",
            "detail": f"La suma de pesos importada es {mefi['weight_sum']}, no 1.00.",
            "sheet": "MEFI",
        })
    if mefe["weight_warning"]:
        warnings.append({
            "title": "Pesos MEFE",
            "detail": f"La suma de pesos importada es {mefe['weight_sum']}, no 1.00.",
            "sheet": "MEFE",
        })
    for row in sgsi_rows + oesi_rows:
        if row["source_mismatch"]:
            warnings.append({
                "title": "Resultado recalculado diferente al Excel fuente",
                "detail": (
                    f"Indicador {row['obj'].metric_id}: "
                    f"fuente={row['obj'].source_compliance}; sistema={row['compliance']}."
                ),
                "sheet": "Dashboard SGSI" if hasattr(row["obj"], "action_plan") else "Dashboard OESI",
            })

    efi = mefi["score_sum"]
    efe = mefe["score_sum"]
    efi_x = max(Decimal("0"), min(Decimal("100"), (Decimal("4") - efi) / Decimal("3") * Decimal("100")))
    efe_y = max(Decimal("0"), min(Decimal("100"), (Decimal("4") - efe) / Decimal("3") * Decimal("100")))

    return {
        "dataset": dataset,
        "sgsi_rows": sgsi_rows,
        "oesi_rows": oesi_rows,
        "sgsi_yes": sgsi_yes,
        "sgsi_total": len(sgsi_rows),
        "sgsi_pct": Decimal(sgsi_yes) * Decimal("100") / Decimal(len(sgsi_rows) or 1),
        "oesi_yes": oesi_yes,
        "oesi_total": len(oesi_rows),
        "oesi_pct": Decimal(oesi_yes) * Decimal("100") / Decimal(len(oesi_rows) or 1),
        "strategic": strategic,
        "security": security,
        "oee_alignments": oee_alignments,
        "requirements": requirements,
        "req_alignments": req_alignments,
        "oee_scores": oee_scores,
        "req_scores": req_scores,
        "oee_obtained": oee_obtained,
        "oee_expected": oee_expected,
        "oee_pct": oee_pct,
        "req_obtained": req_obtained,
        "req_expected": req_expected,
        "req_pct": req_pct,
        "mefi": mefi,
        "mefe": mefe,
        "efi_x": efi_x,
        "efe_y": efe_y,
        "warnings": warnings,
        "traces": list(dataset.cell_traces.order_by("source_sheet", "source_cell")),
        "changes": list(dataset.changes.select_related("created_by").order_by("-created_at")[:80]),
    }
