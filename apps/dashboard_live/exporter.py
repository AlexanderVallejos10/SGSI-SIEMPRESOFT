from decimal import Decimal

from .excel_io import WorkbookPatcher
from .logic import compliance, factor_summary, relation_score
from .models import MatrixType

SHEET_SGSI = "Dashboard SGSI"
SHEET_OESI = "Dashboard OESI"
SHEET_OEE = "Matriz OEE vs OSI (ISO 27001 6."
SHEET_REQ = "Matriz RyEPI vs OSI"
SHEET_MEFI = "MEFI"
SHEET_MEFE = "MEFE"
SHEET_EFIEFE = "EFIEFE"


def export_workbook(dataset):
    patcher = WorkbookPatcher(dataset.file.path)
    security = list(dataset.security_objectives.all())
    oee_alignments = list(dataset.oee_osi_alignments.select_related("security_objective"))
    req_alignments = list(dataset.requirement_osi_alignments.select_related("security_objective"))

    oee_scores = {obj.code: relation_score(oee_alignments, obj) for obj in security}
    req_scores = {obj.code: relation_score(req_alignments, obj) for obj in security}

    oee_obtained = sum(oee_scores.values())
    oee_expected = len(security) * 7
    req_obtained = sum(req_scores.values())
    req_expected = len(security) * 17

    oee_pct = Decimal(oee_obtained) * Decimal("100") / Decimal(oee_expected or 1)
    req_pct = Decimal(req_obtained) * Decimal("100") / Decimal(req_expected or 1)

    for metric in dataset.sgsi_metrics.all():
        row = metric.source_row
        for col, value in (
            ("A", metric.metric_id),
            ("B", metric.description),
            ("C", metric.pdca_cycle),
            ("D", metric.sgsi_process),
            ("E", metric.method),
            ("F", metric.objective),
            ("G", metric.responsible_text),
            ("H", metric.period),
            ("I", metric.indicator),
            ("L", metric.action_plan),
        ):
            if col == "A":
                patcher.number(SHEET_SGSI, f"{col}{row}", value)
            else:
                patcher.string(SHEET_SGSI, f"{col}{row}", value)

        current = oee_pct if metric.metric_id == 1 else req_pct if metric.metric_id == 2 else metric.current_value
        if current is not None:
            patcher.number(SHEET_SGSI, f"J{row}", current * metric.excel_scale)
        else:
            patcher.string(SHEET_SGSI, f"J{row}", metric.current_text or "")
        patcher.string(SHEET_SGSI, f"K{row}", compliance(metric.indicator, current))

    for metric in dataset.oesi_metrics.all():
        row = metric.source_row
        for col, value in (
            ("A", metric.metric_id),
            ("B", metric.description),
            ("C", metric.method),
            ("D", metric.responsible_text),
            ("E", metric.period),
            ("F", metric.indicator),
            ("K", metric.record_label),
        ):
            if col == "A":
                patcher.number(SHEET_OESI, f"{col}{row}", value)
            else:
                patcher.string(SHEET_OESI, f"{col}{row}", value)
        if metric.current_value is not None:
            patcher.number(SHEET_OESI, f"G{row}", metric.current_value * metric.excel_scale)
        else:
            patcher.string(SHEET_OESI, f"G{row}", metric.current_text or "")
        patcher.string(SHEET_OESI, f"H{row}", compliance(metric.indicator, metric.current_value))

    for objective in dataset.strategic_objectives.all():
        patcher.string(SHEET_OEE, f"A{objective.source_row}", objective.code)
        patcher.string(SHEET_OEE, f"B{objective.source_row}", objective.description)

    for objective in security:
        patcher.string(SHEET_OEE, f"{objective.source_column}2", objective.code)
        patcher.string(SHEET_OEE, f"{objective.source_column}3", objective.description)
        patcher.string(SHEET_REQ, f"{objective.source_column}2", objective.code)
        patcher.string(SHEET_REQ, f"{objective.source_column}3", objective.description)

    for alignment in dataset.oee_osi_alignments.all():
        patcher.string(SHEET_OEE, alignment.source_cell, alignment.relation)

    for objective in security:
        patcher.number(SHEET_OEE, f"{objective.source_column}15", oee_scores[objective.code])
    patcher.number(SHEET_OEE, "C18", oee_expected)
    patcher.number(SHEET_OEE, "C19", oee_obtained)
    patcher.number(SHEET_OEE, "C20", oee_pct)

    for requirement in dataset.stakeholder_requirements.all():
        patcher.string(SHEET_REQ, f"A{requirement.source_row}", requirement.stakeholder)
        patcher.string(SHEET_REQ, f"B{requirement.source_row}", requirement.requirement)

    for alignment in dataset.requirement_osi_alignments.all():
        patcher.string(SHEET_REQ, alignment.source_cell, alignment.relation)

    for objective in security:
        patcher.number(SHEET_REQ, f"{objective.source_column}21", req_scores[objective.code])
    patcher.number(SHEET_REQ, "C24", req_expected)
    patcher.number(SHEET_REQ, "C25", req_obtained)
    patcher.number(SHEET_REQ, "C26", req_pct)

    factors = list(dataset.strategic_factors.all())
    mefi = factor_summary(factors, MatrixType.MEFI)
    mefe = factor_summary(factors, MatrixType.MEFE)

    for factor in factors:
        sheet = SHEET_MEFI if factor.matrix_type == MatrixType.MEFI else SHEET_MEFE
        row = factor.source_row
        patcher.string(sheet, f"A{row}", factor.description)
        patcher.number(sheet, f"B{row}", factor.weight)
        patcher.number(sheet, f"C{row}", factor.classification)
        patcher.number(sheet, f"D{row}", factor.score)

    patcher.number(SHEET_MEFI, "D9", mefi["groups"].get("strength", Decimal("0")))
    patcher.number(SHEET_MEFI, "D15", mefi["groups"].get("weakness", Decimal("0")))
    patcher.number(SHEET_MEFI, "B16", mefi["weight_sum"])
    patcher.number(SHEET_MEFI, "D16", mefi["score_sum"])

    patcher.number(SHEET_MEFE, "D9", mefe["groups"].get("opportunity", Decimal("0")))
    patcher.number(SHEET_MEFE, "D17", mefe["groups"].get("threat", Decimal("0")))
    patcher.number(SHEET_MEFE, "B18", mefe["weight_sum"])
    patcher.number(SHEET_MEFE, "D18", mefe["score_sum"])

    for ref in ("B4", "D4", "F4", "B6", "D6", "F6", "B8", "D8", "F8"):
        patcher.string(SHEET_EFIEFE, ref, "")

    efi = mefi["score_sum"]
    efe = mefe["score_sum"]
    col = "B" if efi >= Decimal("3") else "D" if efi >= Decimal("2") else "F"
    row = 4 if efe >= Decimal("3") else 6 if efe >= Decimal("2") else 8
    patcher.string(SHEET_EFIEFE, f"{col}{row}", "X")

    return patcher.save_bytes()
