import os
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter

from django.core.management.base import BaseCommand, CommandError

from apps.documents.models import SourceArtifact


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def column_index(cell_ref):
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    value = 0
    for ch in letters:
        value = value * 26 + (ord(ch.upper()) - 64)
    return value


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


def workbook_sheet_paths(zf):
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels_root = ET.fromstring(
        zf.read("xl/_rels/workbook.xml.rels")
    )

    rels = {}
    for rel in rels_root:
        rid = rel.attrib.get("Id")
        target = rel.attrib.get("Target", "")

        if target.startswith("/"):
            target = target.lstrip("/")
        elif not target.startswith("xl/"):
            target = "xl/" + target.lstrip("/")

        rels[rid] = target

    sheets = []
    for sheet in wb.iter(f"{{{MAIN_NS}}}sheet"):
        name = sheet.attrib.get("name", "")
        rid = sheet.attrib.get(f"{{{REL_NS}}}id")
        if rid in rels:
            sheets.append((name, rels[rid]))

    return sheets


def read_cell(cell, shared_strings):
    cell_type = cell.attrib.get("t")

    if cell_type == "inlineStr":
        texts = [
            node.text or ""
            for node in cell.iter(f"{{{MAIN_NS}}}t")
        ]
        return "".join(texts)

    value_node = cell.find(f"{{{MAIN_NS}}}v")
    raw = "" if value_node is None else (value_node.text or "")

    if cell_type == "s" and raw:
        try:
            return shared_strings[int(raw)]
        except (ValueError, IndexError):
            return raw

    formula = cell.find(f"{{{MAIN_NS}}}f")
    if formula is not None and formula.text:
        if raw:
            return f"={formula.text}  [cache={raw}]"
        return f"={formula.text}"

    return raw


def profile_sheet(zf, sheet_path, shared_strings, show_rows):
    root = ET.fromstring(zf.read(sheet_path))

    rows = []
    nonempty_cells = 0
    formulas = 0
    max_col = 0
    max_row = 0

    for row in root.iter(f"{{{MAIN_NS}}}row"):
        row_num = int(row.attrib.get("r", "0") or "0")
        values = {}

        for cell in row.findall(f"{{{MAIN_NS}}}c"):
            ref = cell.attrib.get("r", "")
            col = column_index(ref)
            value = read_cell(cell, shared_strings)

            if cell.find(f"{{{MAIN_NS}}}f") is not None:
                formulas += 1

            if str(value).strip():
                nonempty_cells += 1
                values[col] = value
                max_col = max(max_col, col)
                max_row = max(max_row, row_num)

        if values:
            rows.append((row_num, values))

    preview = rows[:show_rows]

    return {
        "nonempty_rows": len(rows),
        "nonempty_cells": nonempty_cells,
        "formula_cells": formulas,
        "max_row": max_row,
        "max_col": max_col,
        "preview": preview,
    }


def pretty_row(row_num, values):
    parts = []

    for col in sorted(values):
        value = str(values[col]).replace("\n", " ").strip()
        if len(value) > 100:
            value = value[:97] + "..."
        parts.append(f"C{col}={value}")

    return f"fila {row_num}: " + " | ".join(parts)


class Command(BaseCommand):
    help = (
        "Localiza y perfila los Dashboard SGSI reales importados como "
        "SourceArtifact. No modifica la base de datos."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            default="2026",
            help="Año/nombre a priorizar. Por defecto: 2026.",
        )
        parser.add_argument(
            "--show-rows",
            type=int,
            default=6,
            help="Filas no vacías a mostrar por hoja. Por defecto: 6.",
        )

    def handle(self, *args, **options):
        year = str(options["year"])
        show_rows = max(0, options["show_rows"])

        candidates = (
            SourceArtifact.objects
            .select_related("classification", "source_package")
            .filter(
                duplicate_of__isnull=True,
                classification__is_dashboard_candidate=True,
            )
            .order_by("original_name")
        )

        self.stdout.write("=== DASHBOARDS SGSI CANÓNICOS ===")
        self.stdout.write(
            f"Candidatos: {candidates.count()}"
        )

        for artifact in candidates:
            self.stdout.write(
                f"{artifact.code} | "
                f"{artifact.original_name} | "
                f"verified={artifact.source_verified} | "
                f"file={'SI' if artifact.file else 'NO'} | "
                f"lifecycle={artifact.classification.lifecycle_hint} | "
                f"path={artifact.original_path}"
            )

        target_qs = candidates.filter(
            original_name__icontains=year,
        )

        preferred = (
            target_qs
            .filter(source_verified=True)
            .exclude(file="")
            .order_by(
                "-classification__confidence",
                "original_name",
            )
            .first()
        )

        if preferred is None:
            self.stdout.write("")
            raise CommandError(
                f"No se encontró Dashboard {year} canónico, verificado "
                "y materializado."
            )

        if not preferred.file:
            raise CommandError(
                f"{preferred.code} existe pero no tiene archivo materializado."
            )

        try:
            file_path = preferred.file.path
        except Exception as exc:
            raise CommandError(
                "El storage no expone una ruta local para el archivo: "
                f"{exc}"
            )

        if not os.path.isfile(file_path):
            raise CommandError(
                f"El archivo materializado no existe: {file_path}"
            )

        if not zipfile.is_zipfile(file_path):
            raise CommandError(
                f"El Dashboard seleccionado no es un XLSX válido: {file_path}"
            )

        self.stdout.write("")
        self.stdout.write("=== DASHBOARD SELECCIONADO ===")
        self.stdout.write(
            f"Code: {preferred.code}"
        )
        self.stdout.write(
            f"Nombre: {preferred.original_name}"
        )
        self.stdout.write(
            f"Ruta fuente: {preferred.original_path}"
        )
        self.stdout.write(
            f"Storage: {preferred.file.name}"
        )
        self.stdout.write(
            f"SHA-256: {preferred.checksum_sha256}"
        )
        self.stdout.write(
            f"Tamaño: {preferred.size_bytes} bytes"
        )

        with zipfile.ZipFile(file_path, "r") as zf:
            shared_strings = load_shared_strings(zf)
            sheets = workbook_sheet_paths(zf)

            self.stdout.write("")
            self.stdout.write("=== HOJAS ===")
            self.stdout.write(
                f"Total hojas: {len(sheets)}"
            )

            sheet_stats = []

            for index, (sheet_name, sheet_path) in enumerate(
                sheets,
                start=1,
            ):
                stats = profile_sheet(
                    zf,
                    sheet_path,
                    shared_strings,
                    show_rows,
                )

                sheet_stats.append(
                    (
                        sheet_name,
                        stats["nonempty_rows"],
                        stats["nonempty_cells"],
                        stats["formula_cells"],
                    )
                )

                self.stdout.write("")
                self.stdout.write(
                    f"[{index}] {sheet_name}"
                )
                self.stdout.write(
                    f"    filas no vacías: {stats['nonempty_rows']}"
                )
                self.stdout.write(
                    f"    celdas no vacías: {stats['nonempty_cells']}"
                )
                self.stdout.write(
                    f"    fórmulas: {stats['formula_cells']}"
                )
                self.stdout.write(
                    f"    alcance usado: fila {stats['max_row']} / "
                    f"columna {stats['max_col']}"
                )

                if show_rows and stats["preview"]:
                    self.stdout.write(
                        "    primeras filas no vacías:"
                    )
                    for row_num, values in stats["preview"]:
                        self.stdout.write(
                            "      " + pretty_row(row_num, values)
                        )

        self.stdout.write("")
        self.stdout.write("=== RESUMEN DE HOJAS ===")
        for name, rows, cells, formulas in sheet_stats:
            self.stdout.write(
                f"{name} | filas={rows} | "
                f"celdas={cells} | formulas={formulas}"
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Perfil del Dashboard SGSI completado sin modificar datos."
            )
        )
