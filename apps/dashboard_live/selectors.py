import json
from decimal import Decimal

from django.urls import reverse

from .logic import compliance, factor_summary, relation_score
from .models import DashboardDataset, MatrixType


def current_dataset():
    return DashboardDataset.objects.filter(is_current=True).first()


def dataset_meta(dataset):
    """Datos del formato guardados por el importador (mínimos esperados, tipo de ponderación)."""
    for line in (dataset.notes or "").splitlines():
        if line.startswith("META:"):
            try:
                return json.loads(line[5:])
            except ValueError:
                return {}
    return {}


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

    meta = dataset_meta(dataset)
    averaged = meta.get("ponderacion") == "promedio por grupo"
    mefi = factor_summary(factors, MatrixType.MEFI)
    mefe = factor_summary(factors, MatrixType.MEFE)
    if averaged:  # 2026: cada grupo se promedia; la suma de pesos no tiene que ser 1
        for summary in (mefi, mefe):
            summary["weight_warning"] = False
            # Promedio exacto de cada grupo, como el subtotal del Excel (los pesos guardados van redondeados).
            by_group = {}
            for factor in summary["rows"]:
                by_group.setdefault(factor.group, []).append(Decimal(factor.classification))
            summary["groups"] = {g: sum(v) / Decimal(len(v)) for g, v in by_group.items()}
            summary["score_sum"] = sum(summary["groups"].values(), Decimal("0"))

    oee_scores = {obj.code: relation_score(oee_alignments, obj) for obj in security}
    req_scores = {obj.code: relation_score(req_alignments, obj) for obj in security}

    oee_obtained = sum(oee_scores.values())
    oee_expected = meta.get("oee_minimo") or len(security) * 7
    req_obtained = sum(req_scores.values())
    req_expected = meta.get("req_minimo") or len(security) * 17

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
    if averaged:
        # Escala del Excel 2026 (hoja EFIEFE): ejes de 6 a 1, el 6 arriba a la izquierda.
        clip = lambda v: max(Decimal("1"), min(Decimal("6"), v))
        inset = lambda v: max(Decimal("4"), min(Decimal("96"), v))  # el punto no se pega al borde
        efi_x = inset((Decimal("6") - clip(efi)) / Decimal("5") * Decimal("100"))
        efe_y = inset((Decimal("6") - clip(efe)) / Decimal("5") * Decimal("100"))
    else:
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
        "meta": meta,
        "averaged": averaged,
        "efi": efi,
        "efe": efe,
        "efi_x": efi_x,
        "efe_y": efe_y,
        "warnings": warnings,
        "traces": list(dataset.cell_traces.order_by("source_sheet", "source_cell")),
        "changes": list(dataset.changes.select_related("created_by").order_by("-created_at")[:80]),
    }
