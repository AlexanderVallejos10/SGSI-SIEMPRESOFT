import os
import zipfile
import xml.etree.ElementTree as ET


MAIN_NS = (
    "http://schemas.openxmlformats.org/"
    "spreadsheetml/2006/main"
)
REL_NS = (
    "http://schemas.openxmlformats.org/"
    "officeDocument/2006/relationships"
)


def _col_number(ref):
    letters = "".join(
        ch for ch in ref if ch.isalpha()
    ).upper()

    value = 0
    for ch in letters:
        value = value * 26 + ord(ch) - 64

    return value


def _shared_strings(zf):
    name = "xl/sharedStrings.xml"

    if name not in zf.namelist():
        return []

    root = ET.fromstring(
        zf.read(name)
    )

    output = []

    for item in root.iter(
        f"{{{MAIN_NS}}}si"
    ):
        text = "".join(
            node.text or ""
            for node in item.iter(
                f"{{{MAIN_NS}}}t"
            )
        )
        output.append(text)

    return output


def _sheet_paths(zf):
    workbook = ET.fromstring(
        zf.read("xl/workbook.xml")
    )

    relationships = ET.fromstring(
        zf.read(
            "xl/_rels/workbook.xml.rels"
        )
    )

    rel_map = {}

    for rel in relationships:
        rid = rel.attrib.get("Id")
        target = rel.attrib.get(
            "Target",
            "",
        )

        if target.startswith("/"):
            target = target.lstrip("/")
        elif not target.startswith("xl/"):
            target = (
                "xl/"
                + target.lstrip("/")
            )

        rel_map[rid] = target

    result = []

    for sheet in workbook.iter(
        f"{{{MAIN_NS}}}sheet"
    ):
        name = sheet.attrib.get(
            "name",
            "",
        )

        rid = sheet.attrib.get(
            f"{{{REL_NS}}}id"
        )

        if rid in rel_map:
            result.append(
                (
                    name,
                    rel_map[rid],
                )
            )

    return result


def _value(cell, shared):
    cell_type = cell.attrib.get("t")

    if cell_type == "inlineStr":
        return "".join(
            node.text or ""
            for node in cell.iter(
                f"{{{MAIN_NS}}}t"
            )
        )

    value_node = cell.find(
        f"{{{MAIN_NS}}}v"
    )

    raw = (
        value_node.text or ""
        if value_node is not None
        else ""
    )

    if cell_type == "s" and raw:
        try:
            return shared[int(raw)]
        except (
            ValueError,
            IndexError,
        ):
            return raw

    return raw


def read_xlsx_preview(
    path,
    max_rows=300,
    max_cols=35,
):
    if not os.path.isfile(path):
        raise FileNotFoundError(path)

    if not zipfile.is_zipfile(path):
        raise ValueError(
            "El archivo no es XLSX/XLSM válido."
        )

    sheets = []

    with zipfile.ZipFile(
        path,
        "r",
    ) as zf:
        shared = _shared_strings(zf)

        for (
            sheet_name,
            sheet_path,
        ) in _sheet_paths(zf):
            root = ET.fromstring(
                zf.read(sheet_path)
            )

            rows = []
            max_seen = 0

            for row in root.iter(
                f"{{{MAIN_NS}}}row"
            ):
                if len(rows) >= max_rows:
                    break

                cells = {}

                for cell in row.findall(
                    f"{{{MAIN_NS}}}c"
                ):
                    ref = cell.attrib.get(
                        "r",
                        "",
                    )

                    col = _col_number(ref)

                    if (
                        not col
                        or col > max_cols
                    ):
                        continue

                    value = _value(
                        cell,
                        shared,
                    )

                    if str(value).strip():
                        cells[col] = value
                        max_seen = max(
                            max_seen,
                            col,
                        )

                if cells:
                    rows.append(cells)

            normalized_rows = []

            for cells in rows:
                normalized_rows.append(
                    [
                        cells.get(
                            col,
                            "",
                        )
                        for col in range(
                            1,
                            max_seen + 1,
                        )
                    ]
                )

            sheets.append(
                {
                    "name": sheet_name,
                    "rows": normalized_rows,
                    "column_count": max_seen,
                }
            )

    return sheets


def _col_letters(number):
    letters = ""
    while number:
        number, rest = divmod(number - 1, 26)
        letters = chr(65 + rest) + letters
    return letters


def _is_number(value):
    try:
        float(str(value).replace(",", ""))
        return str(value).strip() != ""
    except ValueError:
        return False


def read_xlsx_grid(path, max_rows=400, max_cols=40):
    """Como read_xlsx_preview, pero conserva el número real de fila y la letra de columna,
    para mostrar la hoja con la misma referencia que en Excel (A1, B7...)."""
    if not os.path.isfile(path) or not zipfile.is_zipfile(path):
        raise ValueError("El archivo no es XLSX/XLSM válido.")
    sheets = []
    with zipfile.ZipFile(path, "r") as zf:
        shared = _shared_strings(zf)
        for sheet_name, sheet_path in _sheet_paths(zf):
            root = ET.fromstring(zf.read(sheet_path))
            rows = []
            max_seen = 0
            truncated = False
            for row in root.iter(f"{{{MAIN_NS}}}row"):
                cells = {}
                for cell in row.findall(f"{{{MAIN_NS}}}c"):
                    col = _col_number(cell.attrib.get("r", ""))
                    if not col or col > max_cols:
                        continue
                    value = _value(cell, shared)
                    if str(value).strip():
                        cells[col] = value
                        max_seen = max(max_seen, col)
                if not cells:
                    continue
                if len(rows) >= max_rows:
                    truncated = True
                    break
                rows.append((int(row.attrib.get("r", len(rows) + 1)), cells))
            sheets.append({
                "name": sheet_name,
                "columns": [_col_letters(c) for c in range(1, max_seen + 1)],
                "rows": [
                    {
                        "number": number,
                        "cells": [
                            {"value": cells.get(c, ""), "numeric": _is_number(cells.get(c, ""))}
                            for c in range(1, max_seen + 1)
                        ],
                    }
                    for number, cells in rows
                ],
                "truncated": truncated,
            })
    return sheets
