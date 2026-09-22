from pathlib import Path

PARSER = 'import zipfile\nimport xml.etree.ElementTree as ET\n\n\nMAIN_NS = (\n    "http://schemas.openxmlformats.org/"\n    "spreadsheetml/2006/main"\n)\n\nREL_NS = (\n    "http://schemas.openxmlformats.org/"\n    "officeDocument/2006/relationships"\n)\n\n\ndef _clean(value):\n    if value is None:\n        return ""\n\n    return " ".join(\n        str(value)\n        .replace("\\xa0", " ")\n        .split()\n    ).strip()\n\n\ndef _column_number(cell_ref):\n    letters = "".join(\n        ch\n        for ch in cell_ref\n        if ch.isalpha()\n    ).upper()\n\n    value = 0\n\n    for ch in letters:\n        value = (\n            value * 26\n            + ord(ch)\n            - 64\n        )\n\n    return value\n\n\ndef _shared_strings(zf):\n    name = "xl/sharedStrings.xml"\n\n    if name not in zf.namelist():\n        return []\n\n    root = ET.fromstring(\n        zf.read(name)\n    )\n\n    values = []\n\n    for item in root.iter(\n        f"{{{MAIN_NS}}}si"\n    ):\n        values.append(\n            "".join(\n                node.text or ""\n                for node in item.iter(\n                    f"{{{MAIN_NS}}}t"\n                )\n            )\n        )\n\n    return values\n\n\ndef _sheet_paths(zf):\n    workbook = ET.fromstring(\n        zf.read(\n            "xl/workbook.xml"\n        )\n    )\n\n    relationships = ET.fromstring(\n        zf.read(\n            "xl/_rels/workbook.xml.rels"\n        )\n    )\n\n    rel_map = {}\n\n    for rel in relationships:\n        target = rel.attrib.get(\n            "Target",\n            "",\n        )\n\n        if target.startswith("/"):\n            target = (\n                target.lstrip("/")\n            )\n        elif not target.startswith(\n            "xl/"\n        ):\n            target = (\n                "xl/"\n                + target.lstrip("/")\n            )\n\n        rel_map[\n            rel.attrib.get("Id")\n        ] = target\n\n    output = {}\n\n    for sheet in workbook.iter(\n        f"{{{MAIN_NS}}}sheet"\n    ):\n        rid = sheet.attrib.get(\n            f"{{{REL_NS}}}id"\n        )\n\n        name = sheet.attrib.get(\n            "name",\n            "",\n        )\n\n        if rid in rel_map:\n            output[name] = (\n                rel_map[rid]\n            )\n\n    return output\n\n\ndef _cell_value(\n    cell,\n    shared,\n):\n    cell_type = (\n        cell.attrib.get("t")\n    )\n\n    if cell_type == "inlineStr":\n        return "".join(\n            node.text or ""\n            for node in cell.iter(\n                f"{{{MAIN_NS}}}t"\n            )\n        )\n\n    value_node = cell.find(\n        f"{{{MAIN_NS}}}v"\n    )\n\n    raw = (\n        value_node.text or ""\n        if value_node is not None\n        else ""\n    )\n\n    if (\n        cell_type == "s"\n        and raw\n    ):\n        try:\n            return shared[\n                int(raw)\n            ]\n        except (\n            ValueError,\n            IndexError,\n        ):\n            return raw\n\n    return raw\n\n\ndef _read_sheet(\n    file_path,\n    sheet_name=None,\n):\n    if not zipfile.is_zipfile(\n        file_path\n    ):\n        raise ValueError(\n            "El archivo no es un "\n            "XLSX/XLSM válido."\n        )\n\n    with zipfile.ZipFile(\n        file_path,\n        "r",\n    ) as zf:\n        shared = (\n            _shared_strings(zf)\n        )\n\n        paths = _sheet_paths(zf)\n\n        if sheet_name:\n            sheet_path = paths.get(\n                sheet_name\n            )\n\n            if not sheet_path:\n                raise ValueError(\n                    "No se encontró la hoja "\n                    f"{sheet_name!r}."\n                )\n        else:\n            if not paths:\n                raise ValueError(\n                    "El Excel no contiene hojas."\n                )\n\n            sheet_path = next(\n                iter(paths.values())\n            )\n\n        root = ET.fromstring(\n            zf.read(sheet_path)\n        )\n\n        rows = []\n\n        for row in root.iter(\n            f"{{{MAIN_NS}}}row"\n        ):\n            row_number = int(\n                row.attrib.get(\n                    "r",\n                    "0",\n                )\n                or 0\n            )\n\n            cells = {}\n\n            for cell in row.findall(\n                f"{{{MAIN_NS}}}c"\n            ):\n                column = (\n                    _column_number(\n                        cell.attrib.get(\n                            "r",\n                            "",\n                        )\n                    )\n                )\n\n                if not column:\n                    continue\n\n                cells[column] = (\n                    _cell_value(\n                        cell,\n                        shared,\n                    )\n                )\n\n            rows.append(\n                (\n                    row_number,\n                    cells,\n                )\n            )\n\n        return rows\n\n\ndef parse_interested_parties(\n    file_path,\n):\n    rows = _read_sheet(\n        file_path\n    )\n\n    start_index = None\n\n    for index, (\n        _,\n        cells,\n    ) in enumerate(rows):\n        first = _clean(\n            cells.get(1)\n        ).upper()\n\n        second = _clean(\n            cells.get(2)\n        ).upper()\n\n        if (\n            "PARTE INTERESADA"\n            in first\n            and "NECESIDADES"\n            in second\n        ):\n            start_index = (\n                index + 1\n            )\n            break\n\n    if start_index is None:\n        raise ValueError(\n            "No se encontró la cabecera "\n            "PARTE INTERESADA / NECESIDADES."\n        )\n\n    output = []\n    current_party = ""\n\n    for (\n        row_number,\n        cells,\n    ) in rows[start_index:]:\n        party = _clean(\n            cells.get(1)\n        )\n\n        need = _clean(\n            cells.get(2)\n        )\n\n        expectation = _clean(\n            cells.get(3)\n        )\n\n        if party:\n            current_party = party\n\n        if (\n            current_party\n            and (\n                need\n                or expectation\n            )\n        ):\n            output.append(\n                {\n                    "source_row":\n                        row_number,\n                    "party_name":\n                        current_party,\n                    "need":\n                        need,\n                    "expectation":\n                        expectation,\n                }\n            )\n\n    return output\n\n\ndef parse_legal_requirements(\n    file_path,\n):\n    rows = _read_sheet(\n        file_path,\n        sheet_name="Documentos",\n    )\n\n    start_index = None\n\n    for index, (\n        _,\n        cells,\n    ) in enumerate(rows):\n        first = _clean(\n            cells.get(1)\n        ).upper()\n\n        second = _clean(\n            cells.get(2)\n        ).upper()\n\n        if (\n            first in {\n                "N°",\n                "Nº",\n                "N",\n            }\n            and "REQUISITO"\n            in second\n        ):\n            start_index = (\n                index + 1\n            )\n            break\n\n    if start_index is None:\n        raise ValueError(\n            "No se encontró la cabecera "\n            "del registro legal."\n        )\n\n    output = []\n\n    for (\n        row_number,\n        cells,\n    ) in rows[start_index:]:\n        item_no = _clean(\n            cells.get(1)\n        )\n\n        requirement = _clean(\n            cells.get(2)\n        )\n\n        promulgated_by = _clean(\n            cells.get(3)\n        )\n\n        location = _clean(\n            cells.get(4)\n        )\n\n        responsible = _clean(\n            cells.get(5)\n        )\n\n        stakeholders = _clean(\n            cells.get(6)\n        )\n\n        status = _clean(\n            cells.get(7)\n        )\n\n        if not any(\n            [\n                item_no,\n                requirement,\n                promulgated_by,\n                location,\n                responsible,\n                stakeholders,\n                status,\n            ]\n        ):\n            continue\n\n        if (\n            not item_no\n            and not requirement\n        ):\n            continue\n\n        output.append(\n            {\n                "source_row":\n                    row_number,\n                "item_no":\n                    item_no,\n                "requirement":\n                    requirement,\n                "promulgated_by":\n                    promulgated_by,\n                "location":\n                    location,\n                "responsible":\n                    responsible,\n                "stakeholders":\n                    stakeholders,\n                "status":\n                    status,\n            }\n        )\n\n    return output\n'

print("=== REPARACIÓN CONTEXT42 V70.2 ===")

path = Path(
    "apps/context42/parser.py"
)

if not path.exists():
    raise SystemExit(
        "ERROR: no existe "
        "apps/context42/parser.py"
    )

backup = path.with_name(
    path.name
    + ".before_context42_v70_2.bak"
)

if not backup.exists():
    backup.write_text(
        path.read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )

path.write_text(
    PARSER,
    encoding="utf-8",
)

print(
    "OK: parser.py ya no depende "
    "de openpyxl."
)

installer = Path(
    "install_context42_v70.py"
)

if installer.exists():
    text = installer.read_text(
        encoding="utf-8"
    )

    ibackup = installer.with_name(
        installer.name
        + ".before_context42_v70_2.bak"
    )

    if not ibackup.exists():
        ibackup.write_text(
            text,
            encoding="utf-8",
        )

    old_import = (
        "from openpyxl "
        "import load_workbook"
    )

    if old_import in text:
        print(
            "AVISO: el instalador local "
            "original contiene openpyxl. "
            "No vuelva a ejecutarlo; "
            "use esta reparación sobre "
            "la instalación actual."
        )

print("")
print("Reparación V70.2 terminada.")
print("El parser usa únicamente la "
      "biblioteca estándar de Python.")
print("")
print("Validación esperada:")
print("- Partes interesadas: 18 filas.")
print("- Lista legal V0.15: 29 filas.")
