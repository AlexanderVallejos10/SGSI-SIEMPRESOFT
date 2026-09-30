import hashlib
import json
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


# ---------------------------------------------------------------------------------------------
# Lectura adaptable: sirve para el Dashboard de 2021 (posiciones fijas) y para el de 2026, que tiene
# otra cantidad de mediciones, 9 OESI, 18 expectativas y MEFI/MEFE sin pesos (promedio por grupo).

def col_letter(index):
    letters = ""
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def max_row(sheet):
    rows = [int(re.sub(r"[A-Z]+", "", ref)) for ref in sheet if re.sub(r"[A-Z]+", "", ref).isdigit()]
    return max(rows, default=1)


def numeric_id(value):
    try:
        return int(Decimal(str(value).strip()))
    except Exception:
        return None


def find_sheet(reader, *prefixes):
    for name in reader.sheet_paths:
        if any(normalize(name).startswith(normalize(p)) for p in prefixes):
            return name
    raise KeyError(f"No se encontró la hoja {prefixes[0]!r} en el Excel del dashboard.")


def _rows_with_numeric_id(sheet):
    seen = set()
    for row in range(2, max_row(sheet) + 1):
        metric_id = numeric_id(c(sheet, f"A{row}")["value"])
        if metric_id is None or metric_id in seen:
            continue  # filas de notas o ID repetido (en 2026 la medición 5 aparece dos veces)
        seen.add(metric_id)
        yield row, metric_id


def import_metrics(dataset, sheet, sheet_name=SHEET_SGSI):
    mappings = {
        "description": "B", "pdca_cycle": "C", "sgsi_process": "D",
        "method": "E", "objective": "F", "responsible_text": "G",
        "period": "H", "indicator": "I", "current_value": "J",
        "source_compliance": "K", "action_plan": "L",
    }
    for row, metric_id in _rows_with_numeric_id(sheet):
        indicator = clean_text(c(sheet, f"I{row}")["value"])
        current_value, current_text, scale = numeric_display(c(sheet, f"J{row}")["value"], indicator)
        responsible = clean_text(c(sheet, f"G{row}")["value"])
        DashboardMetric.objects.create(
            dataset=dataset, metric_id=metric_id, source_row=row,
            description=clean_text(c(sheet, f"B{row}")["value"]),
            pdca_cycle=clean_text(c(sheet, f"C{row}")["value"]),
            sgsi_process=clean_text(c(sheet, f"D{row}")["value"]),
            method=clean_text(c(sheet, f"E{row}")["value"]),
            objective=clean_text(c(sheet, f"F{row}")["value"]),
            responsible_text=responsible, responsible_position=match_position(responsible),
            period=clean_text(c(sheet, f"H{row}")["value"]), indicator=indicator,
            current_value=current_value, current_text=current_text, excel_scale=scale,
            source_compliance=clean_text(c(sheet, f"K{row}")["value"]),
            action_plan=clean_text(c(sheet, f"L{row}")["value"]),
        )
        for field_name, col in mappings.items():
            trace(dataset, "sgsi_metric", metric_id, field_name, sheet_name, f"{col}{row}", c(sheet, f"{col}{row}"))


def import_oesi(dataset, sheet, sheet_name=SHEET_OESI, legacy=False):
    mappings = {
        "description": "B", "method": "C", "responsible_text": "D",
        "period": "E", "indicator": "F", "current_value": "G",
        "source_compliance": "H", "record_label": "K",
    }
    for row, metric_id in _rows_with_numeric_id(sheet):
        indicator = clean_text(c(sheet, f"F{row}")["value"])
        current_value, current_text, scale = numeric_display(
            c(sheet, f"G{row}")["value"], indicator, force_percent=legacy and row in {2, 3, 4},
        )
        responsible = clean_text(c(sheet, f"D{row}")["value"])
        OesiMetric.objects.create(
            dataset=dataset, metric_id=metric_id, source_row=row,
            description=clean_text(c(sheet, f"B{row}")["value"]),
            method=clean_text(c(sheet, f"C{row}")["value"]),
            responsible_text=responsible, responsible_position=match_position(responsible),
            period=clean_text(c(sheet, f"E{row}")["value"]), indicator=indicator,
            current_value=current_value, current_text=current_text, excel_scale=scale,
            source_compliance=clean_text(c(sheet, f"H{row}")["value"]),
            record_label=clean_text(c(sheet, f"K{row}")["value"]),
        )
        for field_name, col in mappings.items():
            trace(dataset, "oesi_metric", metric_id, field_name, sheet_name, f"{col}{row}", c(sheet, f"{col}{row}"))


def _minimum_expected(sheet):
    """Valor de «Mínimo esperado» que calcula el propio Excel bajo cada matriz."""
    for row in range(1, max_row(sheet) + 1):
        for col in ("A", "B"):
            if normalize(c(sheet, f"{col}{row}")["value"]).startswith("minimo esperado"):
                for value_col in ("C", "D"):
                    number = decimal_or_none(c(sheet, f"{value_col}{row}")["value"])
                    if number is not None:
                        return int(number)
    return None


def import_objectives(dataset, oee_sheet, req_sheet, oee_name=SHEET_OEE, req_name=SHEET_REQ):
    security = {}
    col_index = 3
    while True:
        col = col_letter(col_index)
        code = clean_text(c(oee_sheet, f"{col}2")["value"])
        if not code or not normalize(code).startswith(("oesi", "osi")):
            break
        security[col] = SecurityObjective.objects.create(
            dataset=dataset, code=code, description=clean_text(c(oee_sheet, f"{col}3")["value"]),
            source_column=col, sort_order=col_index - 2,
        )
        trace(dataset, "security_objective", code, "description", oee_name, f"{col}3", c(oee_sheet, f"{col}3"))
        col_index += 1

    for row in range(4, max_row(oee_sheet) + 1):
        code = clean_text(c(oee_sheet, f"A{row}")["value"])
        if not normalize(code).startswith("oee"):
            continue
        objective = StrategicObjective.objects.create(
            dataset=dataset, code=code, description=clean_text(c(oee_sheet, f"B{row}")["value"]), source_row=row,
        )
        trace(dataset, "strategic_objective", code, "description", oee_name, f"B{row}", c(oee_sheet, f"B{row}"))
        for col, security_objective in security.items():
            ref = f"{col}{row}"
            relation = clean_text(c(oee_sheet, ref)["value"]).upper()
            alignment = OeeOsiAlignment.objects.create(
                dataset=dataset, strategic_objective=objective, security_objective=security_objective,
                relation=relation if relation in {"P", "S"} else "", source_cell=ref,
            )
            trace(dataset, "oee_osi", alignment.pk, "relation", oee_name, ref, c(oee_sheet, ref))

    current_stakeholder = ""
    for row in range(4, max_row(req_sheet) + 1):
        requirement_text = clean_text(c(req_sheet, f"B{row}")["value"])
        if normalize(requirement_text).startswith(("leyenda", "puntaje", "p ", "s ", "evaluacion", "minimo", "obtenido")):
            break  # empieza la leyenda del Excel
        stakeholder = clean_text(c(req_sheet, f"A{row}")["value"])
        if stakeholder:
            current_stakeholder = stakeholder
        if not requirement_text:
            continue
        requirement = StakeholderRequirement.objects.create(
            dataset=dataset, source_row=row, stakeholder=current_stakeholder, requirement=requirement_text,
        )
        trace(dataset, "stakeholder_requirement", requirement.pk, "requirement", req_name, f"B{row}", c(req_sheet, f"B{row}"))
        for col, security_objective in security.items():
            ref = f"{col}{row}"
            relation = clean_text(c(req_sheet, ref)["value"]).upper()
            alignment = RequirementOsiAlignment.objects.create(
                dataset=dataset, requirement=requirement, security_objective=security_objective,
                relation=relation if relation in {"P", "S"} else "", source_cell=ref,
            )
            trace(dataset, "req_osi", alignment.pk, "relation", req_name, ref, c(req_sheet, ref))
    return {"oee_minimo": _minimum_expected(oee_sheet), "req_minimo": _minimum_expected(req_sheet)}


GROUP_HEADERS = {
    "fortalezas": FactorGroup.STRENGTH, "debilidades": FactorGroup.WEAKNESS,
    "oportunidades": FactorGroup.OPPORTUNITY, "amenazas": FactorGroup.THREAT,
}


def import_factors(dataset, sheet, matrix_type, sheet_name=None):
    """Si el Excel tiene columna «Peso» (2021) se usa; si no (2026), cada grupo se promedia:
    el peso de cada factor es 1 / cantidad de factores de su grupo, igual que el subtotal del Excel."""
    sheet_name = sheet_name or (SHEET_MEFI if matrix_type == MatrixType.MEFI else SHEET_MEFE)
    last = max_row(sheet)
    weighted = any(normalize(c(sheet, f"{col}{r}")["value"]) == "peso" for r in range(1, 5) for col in "BCD")
    group, pending = None, []
    for row in range(2, last + 1):
        description = clean_text(c(sheet, f"A{row}")["value"])
        key = normalize(description)
        if key in GROUP_HEADERS:
            group = GROUP_HEADERS[key]
            continue
        if not description or group is None or key.startswith(("subtotal", "total")):
            continue
        if weighted:
            weight = decimal_or_none(c(sheet, f"B{row}")["value"])
            classification = decimal_or_none(c(sheet, f"C{row}")["value"])
        else:
            weight, classification = None, decimal_or_none(c(sheet, f"B{row}")["value"])
        if classification is None or (weighted and weight is None):
            continue
        pending.append((group, row, description, weight, classification))
    sizes = {}
    for group, *_ in pending:
        sizes[group] = sizes.get(group, 0) + 1
    for group, row, description, weight, classification in pending:
        if weight is None:
            weight = (Decimal("1") / Decimal(sizes[group])).quantize(Decimal("0.000001"))
        factor = StrategicFactor.objects.create(
            dataset=dataset, matrix_type=matrix_type, group=group, source_row=row,
            description=description, weight=weight, classification=int(classification),
        )
        cols = (("description", "A"), ("weight", "B"), ("classification", "C")) if weighted else (("description", "A"), ("classification", "B"))
        for field_name, col in cols:
            trace(dataset, "strategic_factor", factor.pk, field_name, sheet_name, f"{col}{row}", c(sheet, f"{col}{row}"))
    return "pesos" if weighted else "promedio por grupo"


def workbook_summary(path):
    reader = WorkbookReader(path)
    try:
        sgsi = reader.sheet(find_sheet(reader, "Dashboard SGSI"))
        oesi = reader.sheet(find_sheet(reader, "Dashboard OESI"))
        return {
            "sgsi_metrics": sum(1 for _ in _rows_with_numeric_id(sgsi)),
            "oesi_metrics": sum(1 for _ in _rows_with_numeric_id(oesi)),
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
        names = {
            "sgsi": find_sheet(reader, "Dashboard SGSI"),
            "oesi": find_sheet(reader, "Dashboard OESI"),
            "oee": find_sheet(reader, "Matriz OEE"),
            "req": find_sheet(reader, "Matriz RyEPI", "Matriz EPI"),
            "mefi": find_sheet(reader, "MEFI"),
            "mefe": find_sheet(reader, "MEFE"),
        }
        legacy = names["oee"] == SHEET_OEE  # formato 2021, con los porcentajes de OESI en otra escala
        import_metrics(dataset, reader.sheet(names["sgsi"]), names["sgsi"])
        import_oesi(dataset, reader.sheet(names["oesi"]), names["oesi"], legacy=legacy)
        meta = import_objectives(dataset, reader.sheet(names["oee"]), reader.sheet(names["req"]), names["oee"], names["req"])
        meta["ponderacion"] = import_factors(dataset, reader.sheet(names["mefi"]), MatrixType.MEFI, names["mefi"])
        import_factors(dataset, reader.sheet(names["mefe"]), MatrixType.MEFE, names["mefe"])
    finally:
        reader.close()

    # Datos del formato que usa el tablero (mínimos esperados y tipo de ponderación).
    dataset.notes = (dataset.notes + "\n" if dataset.notes else "") + "META:" + json.dumps(meta, ensure_ascii=False)
    dataset.save(update_fields=["notes"])
    return dataset
