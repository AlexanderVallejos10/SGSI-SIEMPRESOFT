import hashlib
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.dashboard.models import (
    AlignmentMatrixType,
    DashboardSnapshot,
    DashboardSourceRow,
    ObjectiveAlignment,
    SGSIMetric,
    SecurityObjective,
    StrategicFactor,
    StrategicFactorType,
)
from apps.documents.models import SourceArtifact


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

SHEET_SGSI = "Dashboard SGSI"
SHEET_OESI = "Dashboard OESI"
SHEET_OEE = "Matriz OEE vs OSI"
SHEET_EPI = "Matriz EPI vs OSI"
SHEET_MEFI = "MEFI"
SHEET_MEFE = "MEFE"

REQUIRED_SHEETS = {
    "Rendimiento SGSI",
    SHEET_SGSI,
    "Rendimiento OESI",
    SHEET_OESI,
    SHEET_OEE,
    SHEET_EPI,
    SHEET_MEFI,
    SHEET_MEFE,
    "EFIEFE",
}


def col_index(cell_ref):
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    value = 0
    for ch in letters:
        value = value * 26 + (ord(ch.upper()) - 64)
    return value


def col_letters(cell_ref):
    return "".join(ch for ch in cell_ref if ch.isalpha()).upper()


def as_decimal(value):
    value = str(value or "").strip()
    if not value:
        return None

    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def normalized_text(value):
    return " ".join(str(value or "").strip().casefold().split())


def load_shared_strings(zf):
    name = "xl/sharedStrings.xml"
    if name not in zf.namelist():
        return []

    root = ET.fromstring(zf.read(name))
    values = []

    for si in root.iter(f"{{{MAIN_NS}}}si"):
        texts = [
            node.text or ""
            for node in si.iter(f"{{{MAIN_NS}}}t")
        ]
        values.append("".join(texts))

    return values


def load_styles(zf):
    name = "xl/styles.xml"
    if name not in zf.namelist():
        return {}

    root = ET.fromstring(zf.read(name))

    custom_numfmts = {}
    numfmts = root.find(f"{{{MAIN_NS}}}numFmts")
    if numfmts is not None:
        for numfmt in numfmts:
            num_id = numfmt.attrib.get("numFmtId")
            code = numfmt.attrib.get("formatCode", "")
            if num_id:
                custom_numfmts[int(num_id)] = code

    builtin = {
        0: "General",
        1: "0",
        2: "0.00",
        9: "0%",
        10: "0.00%",
    }

    style_formats = {}
    cell_xfs = root.find(f"{{{MAIN_NS}}}cellXfs")

    if cell_xfs is not None:
        for index, xf in enumerate(cell_xfs):
            num_id = int(xf.attrib.get("numFmtId", "0"))
            style_formats[index] = custom_numfmts.get(
                num_id,
                builtin.get(num_id, str(num_id)),
            )

    return style_formats


def workbook_sheet_paths(zf):
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rel_root = ET.fromstring(
        zf.read("xl/_rels/workbook.xml.rels")
    )

    rels = {}
    for rel in rel_root:
        rid = rel.attrib.get("Id")
        target = rel.attrib.get("Target", "")

        if target.startswith("/"):
            target = target.lstrip("/")
        elif not target.startswith("xl/"):
            target = "xl/" + target.lstrip("/")

        rels[rid] = target

    result = {}

    for sheet in wb.iter(f"{{{MAIN_NS}}}sheet"):
        name = sheet.attrib.get("name", "")
        rid = sheet.attrib.get(f"{{{REL_NS}}}id")
        if rid in rels:
            result[name] = rels[rid]

    return result


def read_cell(cell, shared_strings, style_formats):
    cell_type = cell.attrib.get("t")
    style_index = int(cell.attrib.get("s", "0") or "0")

    formula_node = cell.find(f"{{{MAIN_NS}}}f")
    value_node = cell.find(f"{{{MAIN_NS}}}v")

    formula = (
        formula_node.text or ""
        if formula_node is not None
        else ""
    )

    raw = (
        value_node.text or ""
        if value_node is not None
        else ""
    )

    if cell_type == "inlineStr":
        texts = [
            node.text or ""
            for node in cell.iter(f"{{{MAIN_NS}}}t")
        ]
        value = "".join(texts)
    elif cell_type == "s" and raw:
        try:
            value = shared_strings[int(raw)]
        except (ValueError, IndexError):
            value = raw
    elif cell_type == "b":
        value = "TRUE" if raw == "1" else "FALSE"
    else:
        value = raw

    return {
        "value": value,
        "formula": formula,
        "number_format": style_formats.get(style_index, ""),
    }


def read_sheet_rows(zf, sheet_path, shared_strings, style_formats):
    root = ET.fromstring(zf.read(sheet_path))
    rows = []

    for row in root.iter(f"{{{MAIN_NS}}}row"):
        row_number = int(row.attrib.get("r", "0") or "0")
        cells = {}

        for cell in row.findall(f"{{{MAIN_NS}}}c"):
            ref = cell.attrib.get("r", "")
            info = read_cell(
                cell,
                shared_strings,
                style_formats,
            )

            if (
                str(info["value"]).strip()
                or str(info["formula"]).strip()
            ):
                cells[col_letters(ref)] = info

        if cells:
            rows.append((row_number, cells))

    return rows


def cell_value(cells, letter):
    return str(cells.get(letter, {}).get("value", "") or "").strip()


def cell_formula(cells, letter):
    return str(cells.get(letter, {}).get("formula", "") or "").strip()


def cell_format(cells, letter):
    return str(
        cells.get(letter, {}).get("number_format", "") or ""
    ).strip()


def snapshot_code(year, checksum):
    return f"DASH-{year}-{checksum[:16].upper()}"


def choose_dashboard_artifact(year):
    qs = (
        SourceArtifact.objects
        .select_related("classification")
        .filter(
            duplicate_of__isnull=True,
            source_verified=True,
            classification__is_dashboard_candidate=True,
            original_name__icontains=str(year),
        )
        .exclude(file="")
        .order_by(
            "-classification__confidence",
            "original_name",
        )
    )

    exact = qs.filter(
        original_name__iexact=(
            f"Dashboard SGSI de SIEMPRESOFT_{year}.xlsx"
        )
    ).first()

    return exact or qs.first()


def import_raw_rows(snapshot, rows_by_sheet):
    count = 0

    for sheet_name, rows in rows_by_sheet.items():
        for row_number, cells in rows:
            DashboardSourceRow.objects.update_or_create(
                snapshot=snapshot,
                sheet_name=sheet_name,
                row_number=row_number,
                defaults={
                    "payload": cells,
                },
            )
            count += 1

    return count


def import_sgsi_metrics(snapshot, rows):
    count = 0

    for row_number, cells in rows:
        if row_number == 1:
            continue

        description = cell_value(cells, "B")
        if not description:
            continue

        SGSIMetric.objects.update_or_create(
            snapshot=snapshot,
            source_row=row_number,
            defaults={
                "measurement_id": cell_value(cells, "A")[:30],
                "description": description,
                "pdca_cycle": cell_value(cells, "C")[:10],
                "sgsi_process": cell_value(cells, "D"),
                "method_resources": cell_value(cells, "E"),
                "measurement_objective": cell_value(cells, "F"),
                "responsible": cell_value(cells, "G")[:180],
                "update_period": cell_value(cells, "H")[:120],
                "indicator": cell_value(cells, "I")[:120],
                "current_value_raw": cell_value(cells, "J")[:120],
                "current_value_numeric": as_decimal(
                    cell_value(cells, "J")
                ),
                "current_number_format": cell_format(cells, "J")[:120],
                "calculation_formula": cell_formula(cells, "J"),
                "compliance_raw": cell_value(cells, "K")[:30],
                "compliance_formula": cell_formula(cells, "K"),
                "recommended_actions": cell_value(cells, "L"),
            },
        )
        count += 1

    return count


def import_oesi(snapshot, rows):
    count = 0

    for row_number, cells in rows:
        if row_number == 1:
            continue

        measurement_id = cell_value(cells, "A")
        description = cell_value(cells, "B")

        if not measurement_id or not description:
            continue

        SecurityObjective.objects.update_or_create(
            snapshot=snapshot,
            source_row=row_number,
            defaults={
                "measurement_id": measurement_id[:30],
                "description": description,
                "method_resources": cell_value(cells, "C"),
                "responsible": cell_value(cells, "D")[:180],
                "calculation_period": cell_value(cells, "E")[:120],
                "indicator": cell_value(cells, "F")[:120],
                "current_value_raw": cell_value(cells, "G")[:120],
                "current_value_numeric": as_decimal(
                    cell_value(cells, "G")
                ),
                "current_number_format": cell_format(cells, "G")[:120],
                "calculation_formula": cell_formula(cells, "G"),
                "compliance_raw": cell_value(cells, "H")[:30],
                "compliance_formula": cell_formula(cells, "H"),
                "source_compliance_override": cell_value(
                    cells,
                    "I",
                )[:30],
            },
        )
        count += 1

    return count


def count_oee_alignment(rows):
    headers = {}
    count = 0

    for row_number, cells in rows:
        if row_number == 2:
            for letter in (
                "C", "D", "E", "F", "G", "H", "I", "J", "K"
            ):
                value = cell_value(cells, letter)
                if value:
                    headers[letter] = value
            continue

        source_code = cell_value(cells, "A")
        description = cell_value(cells, "B")

        if not source_code.startswith("OEE") or not description:
            continue

        for letter in headers:
            if cell_value(cells, letter).upper() in {"P", "S"}:
                count += 1

    return count


def count_epi_alignment(rows):
    headers = {}
    count = 0

    for row_number, cells in rows:
        if row_number == 2:
            for letter in (
                "C", "D", "E", "F", "G", "H", "I", "J", "K"
            ):
                value = cell_value(cells, letter)
                if value:
                    headers[letter] = value
            continue

        description = cell_value(cells, "B")
        if not description:
            continue

        for letter in headers:
            if cell_value(cells, letter).upper() in {"P", "S"}:
                count += 1

    return count


def count_factors(rows):
    count = 0

    for row_number, cells in rows:
        label = cell_value(cells, "A")
        classification = as_decimal(cell_value(cells, "B"))

        if (
            label
            and classification is not None
            and 0 <= classification <= 10
        ):
            count += 1

    return count


def import_oee_alignment(snapshot, rows):
    headers = {}
    count = 0

    for row_number, cells in rows:
        if row_number == 2:
            for letter in (
                "C", "D", "E", "F", "G", "H", "I", "J", "K"
            ):
                value = cell_value(cells, letter)
                if value:
                    headers[letter] = value
            continue

        source_code = cell_value(cells, "A")
        description = cell_value(cells, "B")

        if not source_code.startswith("OEE") or not description:
            continue

        for letter, objective_code in headers.items():
            relation = cell_value(cells, letter).upper()

            if relation not in {"P", "S"}:
                continue

            ObjectiveAlignment.objects.update_or_create(
                snapshot=snapshot,
                matrix_type=AlignmentMatrixType.OEE_OSI,
                source_row=row_number,
                objective_code=objective_code[:30],
                defaults={
                    "source_code": source_code[:80],
                    "source_group": "",
                    "source_description": description,
                    "relation_type": relation,
                },
            )
            count += 1

    return count


def import_epi_alignment(snapshot, rows):
    headers = {}
    current_group = ""
    count = 0

    for row_number, cells in rows:
        if row_number == 2:
            for letter in (
                "C", "D", "E", "F", "G", "H", "I", "J", "K"
            ):
                value = cell_value(cells, letter)
                if value:
                    headers[letter] = value
            continue

        group = cell_value(cells, "A")
        description = cell_value(cells, "B")

        if group:
            current_group = group

        if not description:
            continue

        for letter, objective_code in headers.items():
            relation = cell_value(cells, letter).upper()

            if relation not in {"P", "S"}:
                continue

            ObjectiveAlignment.objects.update_or_create(
                snapshot=snapshot,
                matrix_type=AlignmentMatrixType.EPI_OSI,
                source_row=row_number,
                objective_code=objective_code[:30],
                defaults={
                    "source_code": "",
                    "source_group": current_group[:180],
                    "source_description": description,
                    "relation_type": relation,
                },
            )
            count += 1

    return count


def import_factors(snapshot, rows, factor_type):
    count = 0
    category = ""

    category_names = {
        "fortalezas",
        "debilidades",
        "oportunidades",
        "amenazas",
    }

    for row_number, cells in rows:
        label = cell_value(cells, "A")
        classification_raw = cell_value(cells, "B")

        if not label:
            continue

        normalized = normalized_text(label)

        if normalized in category_names:
            category = normalized
            continue

        classification = as_decimal(classification_raw)

        if classification is None:
            continue

        # Las clasificaciones de factores del libro son escalas pequeñas.
        # Totales, coordenadas u otras cifras quedan preservadas en raw rows,
        # pero no se interpretan como factores.
        if classification < 0 or classification > 10:
            continue

        StrategicFactor.objects.update_or_create(
            snapshot=snapshot,
            factor_type=factor_type,
            source_row=row_number,
            defaults={
                "category": category[:40],
                "factor": label,
                "classification": classification,
            },
        )
        count += 1

    return count


class Command(BaseCommand):
    help = (
        "Importa el Dashboard SGSI real de un año desde SourceArtifact. "
        "Normaliza métricas SGSI, objetivos OESI, matrices OEE/EPI y "
        "factores MEFI/MEFE, conservando además todas las filas originales. "
        "Por defecto es PREVIEW."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            default=2026,
            help="Año del Dashboard. Por defecto: 2026.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Guarda el snapshot y datos normalizados.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        year = options["year"]
        apply_changes = options["apply"]

        artifact = choose_dashboard_artifact(year)

        if artifact is None:
            raise CommandError(
                f"No se encontró Dashboard SGSI {year} "
                "verificado y materializado."
            )

        try:
            file_path = artifact.file.path
        except Exception as exc:
            raise CommandError(
                f"No se pudo resolver la ruta storage: {exc}"
            )

        if not os.path.isfile(file_path):
            raise CommandError(
                f"No existe el archivo materializado: {file_path}"
            )

        if not zipfile.is_zipfile(file_path):
            raise CommandError(
                f"El archivo no es un XLSX válido: {file_path}"
            )

        with zipfile.ZipFile(file_path, "r") as zf:
            shared_strings = load_shared_strings(zf)
            style_formats = load_styles(zf)
            sheet_paths = workbook_sheet_paths(zf)

            missing = sorted(REQUIRED_SHEETS - set(sheet_paths))
            if missing:
                raise CommandError(
                    "Faltan hojas requeridas: "
                    + ", ".join(missing)
                )

            rows_by_sheet = {
                sheet_name: read_sheet_rows(
                    zf,
                    sheet_path,
                    shared_strings,
                    style_formats,
                )
                for sheet_name, sheet_path in sheet_paths.items()
            }

        raw_row_count = sum(
            len(rows)
            for rows in rows_by_sheet.values()
        )

        sgsi_count = sum(
            1
            for row_number, cells in rows_by_sheet[SHEET_SGSI]
            if row_number > 1 and cell_value(cells, "B")
        )

        oesi_count = sum(
            1
            for row_number, cells in rows_by_sheet[SHEET_OESI]
            if (
                row_number > 1
                and cell_value(cells, "A")
                and cell_value(cells, "B")
            )
        )

        oee_count = count_oee_alignment(
            rows_by_sheet[SHEET_OEE]
        )
        epi_count = count_epi_alignment(
            rows_by_sheet[SHEET_EPI]
        )
        mefi_count = count_factors(
            rows_by_sheet[SHEET_MEFI]
        )
        mefe_count = count_factors(
            rows_by_sheet[SHEET_MEFE]
        )

        snapshot = None
        imported_raw = 0
        imported_sgsi = 0
        imported_oesi = 0
        imported_oee = 0
        imported_epi = 0
        imported_mefi = 0
        imported_mefe = 0

        if apply_changes:
            DashboardSnapshot.objects.filter(
                year=year,
                is_active=True,
            ).exclude(
                source_sha256=artifact.checksum_sha256,
            ).update(
                is_active=False,
            )

            snapshot, _ = DashboardSnapshot.objects.update_or_create(
                year=year,
                source_sha256=artifact.checksum_sha256,
                defaults={
                    "code": snapshot_code(
                        year,
                        artifact.checksum_sha256,
                    ),
                    "source_artifact": artifact,
                    "source_name": artifact.original_name,
                    "is_active": True,
                    "notes": (
                        "Importación estructurada desde el Dashboard SGSI "
                        "original; se conserva trazabilidad por hoja y fila."
                    ),
                },
            )

            imported_raw = import_raw_rows(
                snapshot,
                rows_by_sheet,
            )

            imported_sgsi = import_sgsi_metrics(
                snapshot,
                rows_by_sheet[SHEET_SGSI],
            )

            imported_oesi = import_oesi(
                snapshot,
                rows_by_sheet[SHEET_OESI],
            )

            imported_oee = import_oee_alignment(
                snapshot,
                rows_by_sheet[SHEET_OEE],
            )

            imported_epi = import_epi_alignment(
                snapshot,
                rows_by_sheet[SHEET_EPI],
            )

            imported_mefi = import_factors(
                snapshot,
                rows_by_sheet[SHEET_MEFI],
                StrategicFactorType.INTERNAL,
            )

            imported_mefe = import_factors(
                snapshot,
                rows_by_sheet[SHEET_MEFE],
                StrategicFactorType.EXTERNAL,
            )

        self.stdout.write("=== IMPORTACIÓN DASHBOARD SGSI ===")
        self.stdout.write(
            f"Modo: {'APPLY' if apply_changes else 'PREVIEW'}"
        )
        self.stdout.write(
            f"Año: {year}"
        )
        self.stdout.write(
            f"SourceArtifact: {artifact.code}"
        )
        self.stdout.write(
            f"Archivo: {artifact.original_name}"
        )
        self.stdout.write(
            f"SHA-256: {artifact.checksum_sha256}"
        )
        self.stdout.write(
            f"Hojas: {len(rows_by_sheet)}"
        )
        self.stdout.write(
            f"Filas originales no vacías: {raw_row_count}"
        )
        self.stdout.write(
            f"Métricas SGSI previstas: {sgsi_count}"
        )
        self.stdout.write(
            f"Objetivos OESI previstos: {oesi_count}"
        )
        self.stdout.write(
            f"Relaciones OEE↔OESI previstas: {oee_count}"
        )
        self.stdout.write(
            f"Relaciones EPI↔OESI previstas: {epi_count}"
        )
        self.stdout.write(
            f"Factores MEFI previstos: {mefi_count}"
        )
        self.stdout.write(
            f"Factores MEFE previstos: {mefe_count}"
        )

        if not apply_changes:
            transaction.set_rollback(True)
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "PREVIEW: no se modificó PostgreSQL."
                )
            )
            return

        self.stdout.write("")
        self.stdout.write("=== NORMALIZACIÓN PERSISTIDA ===")
        self.stdout.write(
            f"Raw rows: {imported_raw}"
        )
        self.stdout.write(
            f"Métricas SGSI: {imported_sgsi}"
        )
        self.stdout.write(
            f"Objetivos OESI: {imported_oesi}"
        )
        self.stdout.write(
            f"Relaciones OEE↔OESI: {imported_oee}"
        )
        self.stdout.write(
            f"Relaciones EPI↔OESI: {imported_epi}"
        )
        self.stdout.write(
            f"Factores MEFI: {imported_mefi}"
        )
        self.stdout.write(
            f"Factores MEFE: {imported_mefe}"
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Dashboard SGSI importado y normalizado."
            )
        )
