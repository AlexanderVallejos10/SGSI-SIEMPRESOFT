import hashlib
import re
import unicodedata
from decimal import Decimal
from pathlib import Path

from django.core.files import File
from django.db import transaction

from apps.organization.models import Position

from .excel_io import WorkbookReader, clean_text, decimal_or_none, numeric_display
from .models import (
    DashboardCellTrace,
    DashboardDataset,
    DashboardMetric,
    FactorGroup,
    MatrixType,
    OeeOsiAlignment,
    OesiMetric,
    RequirementOsiAlignment,
    SecurityObjective,
    StakeholderRequirement,
    StrategicFactor,
    StrategicObjective,
)

SHEET_SGSI = "Dashboard SGSI"
SHEET_OESI = "Dashboard OESI"
SHEET_OEE = "Matriz OEE vs OSI (ISO 27001 6."
SHEET_REQ = "Matriz RyEPI vs OSI"
SHEET_MEFI = "MEFI"
SHEET_MEFE = "MEFE"


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def match_position(text):
    needle = normalize(text)
    if not needle:
        return None
    positions = list(
        Position.objects.filter(is_active=True).select_related("area").order_by("title")
    )
    exact = next((p for p in positions if normalize(p.title) == needle), None)
    if exact:
        return exact
    return next(
        (
            p for p in positions
            if needle in normalize(p.title) or normalize(p.title) in needle
        ),
        None,
    )


def c(sheet, ref):
    return sheet.get(ref, {"value": "", "formula": "", "style": ""})


def trace(dataset, entity_type, entity_key, field_name, sheet_name, cell_ref, cell_data):
    DashboardCellTrace.objects.create(
        dataset=dataset,
        entity_type=entity_type,
        entity_key=str(entity_key),
        field_name=field_name,
        source_sheet=sheet_name,
        source_cell=cell_ref,
        source_formula=cell_data.get("formula") or "",
        source_value=clean_text(cell_data.get("value", "")),
    )


def import_metrics(dataset, sheet):
    mappings = {
        "description": "B", "pdca_cycle": "C", "sgsi_process": "D",
        "method": "E", "objective": "F", "responsible_text": "G",
        "period": "H", "indicator": "I", "current_value": "J",
        "source_compliance": "K", "action_plan": "L",
    }
    for row in range(2, 12):
        metric_id = int(Decimal(c(sheet, f"A{row}")["value"]))
        indicator = clean_text(c(sheet, f"I{row}")["value"])
        current_value, current_text, scale = numeric_display(
            c(sheet, f"J{row}")["value"], indicator
        )
        responsible = clean_text(c(sheet, f"G{row}")["value"])
        metric = DashboardMetric.objects.create(
            dataset=dataset,
            metric_id=metric_id,
            source_row=row,
            description=clean_text(c(sheet, f"B{row}")["value"]),
            pdca_cycle=clean_text(c(sheet, f"C{row}")["value"]),
            sgsi_process=clean_text(c(sheet, f"D{row}")["value"]),
            method=clean_text(c(sheet, f"E{row}")["value"]),
            objective=clean_text(c(sheet, f"F{row}")["value"]),
            responsible_text=responsible,
            responsible_position=match_position(responsible),
            period=clean_text(c(sheet, f"H{row}")["value"]),
            indicator=indicator,
            current_value=current_value,
            current_text=current_text,
            excel_scale=scale,
            source_compliance=clean_text(c(sheet, f"K{row}")["value"]),
            action_plan=clean_text(c(sheet, f"L{row}")["value"]),
        )
        for field_name, col in mappings.items():
            trace(dataset, "sgsi_metric", metric_id, field_name, SHEET_SGSI, f"{col}{row}", c(sheet, f"{col}{row}"))


def import_oesi(dataset, sheet):
    mappings = {
        "description": "B", "method": "C", "responsible_text": "D",
        "period": "E", "indicator": "F", "current_value": "G",
        "source_compliance": "H", "record_label": "K",
    }
    for row in range(2, 6):
        metric_id = int(Decimal(c(sheet, f"A{row}")["value"]))
        indicator = clean_text(c(sheet, f"F{row}")["value"])
        current_value, current_text, scale = numeric_display(
            c(sheet, f"G{row}")["value"],
            indicator,
            force_percent=row in {2, 3, 4},
        )
        responsible = clean_text(c(sheet, f"D{row}")["value"])
        metric = OesiMetric.objects.create(
            dataset=dataset,
            metric_id=metric_id,
            source_row=row,
            description=clean_text(c(sheet, f"B{row}")["value"]),
            method=clean_text(c(sheet, f"C{row}")["value"]),
            responsible_text=responsible,
            responsible_position=match_position(responsible),
            period=clean_text(c(sheet, f"E{row}")["value"]),
            indicator=indicator,
            current_value=current_value,
            current_text=current_text,
            excel_scale=scale,
            source_compliance=clean_text(c(sheet, f"H{row}")["value"]),
            record_label=clean_text(c(sheet, f"K{row}")["value"]),
        )
        for field_name, col in mappings.items():
            trace(dataset, "oesi_metric", metric_id, field_name, SHEET_OESI, f"{col}{row}", c(sheet, f"{col}{row}"))


def import_objectives(dataset, oee_sheet, req_sheet):
    security = {}
    for index, col in enumerate(("C", "D", "E", "F"), start=1):
        code = clean_text(c(oee_sheet, f"{col}2")["value"])
        objective = SecurityObjective.objects.create(
            dataset=dataset,
            code=code,
            description=clean_text(c(oee_sheet, f"{col}3")["value"]),
            source_column=col,
            sort_order=index,
        )
        security[col] = objective
        trace(dataset, "security_objective", code, "description", SHEET_OEE, f"{col}3", c(oee_sheet, f"{col}3"))

    for row in range(4, 10):
        code = clean_text(c(oee_sheet, f"A{row}")["value"])
        objective = StrategicObjective.objects.create(
            dataset=dataset,
            code=code,
            description=clean_text(c(oee_sheet, f"B{row}")["value"]),
            source_row=row,
        )
        trace(dataset, "strategic_objective", code, "description", SHEET_OEE, f"B{row}", c(oee_sheet, f"B{row}"))
        for col in ("C", "D", "E", "F"):
            ref = f"{col}{row}"
            relation = clean_text(c(oee_sheet, ref)["value"]).upper()
            if relation not in {"P", "S"}:
                relation = ""
            alignment = OeeOsiAlignment.objects.create(
                dataset=dataset,
                strategic_objective=objective,
                security_objective=security[col],
                relation=relation,
                source_cell=ref,
            )
            trace(dataset, "oee_osi", alignment.pk, "relation", SHEET_OEE, ref, c(oee_sheet, ref))

    current_stakeholder = ""
    for row in range(4, 16):
        stakeholder = clean_text(c(req_sheet, f"A{row}")["value"])
        if stakeholder:
            current_stakeholder = stakeholder
        requirement_text = clean_text(c(req_sheet, f"B{row}")["value"])
        if not requirement_text:
            continue
        requirement = StakeholderRequirement.objects.create(
            dataset=dataset,
            source_row=row,
            stakeholder=current_stakeholder,
            requirement=requirement_text,
        )
        trace(dataset, "stakeholder_requirement", requirement.pk, "requirement", SHEET_REQ, f"B{row}", c(req_sheet, f"B{row}"))
        for col in ("C", "D", "E", "F"):
            ref = f"{col}{row}"
            relation = clean_text(c(req_sheet, ref)["value"]).upper()
            if relation not in {"P", "S"}:
                relation = ""
            alignment = RequirementOsiAlignment.objects.create(
                dataset=dataset,
                requirement=requirement,
                security_objective=security[col],
                relation=relation,
                source_cell=ref,
            )
            trace(dataset, "req_osi", alignment.pk, "relation", SHEET_REQ, ref, c(req_sheet, ref))


def import_factors(dataset, sheet, matrix_type):
    if matrix_type == MatrixType.MEFI:
        sections = [(FactorGroup.STRENGTH, range(4, 9)), (FactorGroup.WEAKNESS, range(11, 15))]
        sheet_name = SHEET_MEFI
    else:
        sections = [(FactorGroup.OPPORTUNITY, range(4, 9)), (FactorGroup.THREAT, range(11, 17))]
        sheet_name = SHEET_MEFE

    for group, rows in sections:
        for row in rows:
            description = clean_text(c(sheet, f"A{row}")["value"])
            if not description:
                continue
            weight = decimal_or_none(c(sheet, f"B{row}")["value"])
            classification = decimal_or_none(c(sheet, f"C{row}")["value"])
            if weight is None or classification is None:
                continue
            factor = StrategicFactor.objects.create(
                dataset=dataset,
                matrix_type=matrix_type,
                group=group,
                source_row=row,
                description=description,
                weight=weight,
                classification=int(classification),
            )
            for field_name, col in (("description", "A"), ("weight", "B"), ("classification", "C")):
                trace(dataset, "strategic_factor", factor.pk, field_name, sheet_name, f"{col}{row}", c(sheet, f"{col}{row}"))


def workbook_summary(path):
    reader = WorkbookReader(path)
    try:
        return {
            "sgsi_metrics": 10,
            "oesi_metrics": 4,
            "oee_objectives": 6,
            "security_objectives": 4,
            "requirements": 12,
            "mefi_factors": 9,
            "mefe_factors": 11,
        }
    finally:
        reader.close()


@transaction.atomic
def import_workbook(*, path, version_label="", notes="", actor=None, original_name=None, apply_changes=True):
    path = Path(path)
    checksum = sha256_file(path)
    existing = DashboardDataset.objects.filter(checksum_sha256=checksum).first()

    if existing:
        if apply_changes:
            DashboardDataset.objects.filter(is_current=True).exclude(pk=existing.pk).update(is_current=False)
            existing.is_current = True
            existing.updated_by = actor
            existing.save(update_fields=("is_current", "updated_by", "updated_at"))
        return existing

    if not apply_changes:
        return workbook_summary(path)

    DashboardDataset.objects.filter(is_current=True).update(is_current=False)
    dataset = DashboardDataset(
        code="DASHLIVE-" + checksum[:16].upper(),
        original_name=original_name or path.name,
        checksum_sha256=checksum,
        version_label=version_label,
        is_current=True,
        notes=notes,
        created_by=actor,
        updated_by=actor,
    )

    with open(path, "rb") as handle:
        dataset.file.save(original_name or path.name, File(handle), save=False)
        dataset.save()

    reader = WorkbookReader(path)
    try:
        import_metrics(dataset, reader.sheet(SHEET_SGSI))
        import_oesi(dataset, reader.sheet(SHEET_OESI))
        import_objectives(dataset, reader.sheet(SHEET_OEE), reader.sheet(SHEET_REQ))
        import_factors(dataset, reader.sheet(SHEET_MEFI), MatrixType.MEFI)
        import_factors(dataset, reader.sheet(SHEET_MEFE), MatrixType.MEFE)
    finally:
        reader.close()

    return dataset
