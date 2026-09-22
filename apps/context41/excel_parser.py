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

    root = ET.fromstring(zf.read(name))
    values = []

    for item in root.iter(f"{{{MAIN_NS}}}si"):
        values.append(
            "".join(
                node.text or ""
                for node in item.iter(
                    f"{{{MAIN_NS}}}t"
                )
            )
        )

    return values


def _sheet_paths(zf):
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels_root = ET.fromstring(
        zf.read("xl/_rels/workbook.xml.rels")
    )

    rels = {}

    for rel in rels_root:
        target = rel.attrib.get("Target", "")
        if target.startswith("/"):
            target = target.lstrip("/")
        elif not target.startswith("xl/"):
            target = "xl/" + target.lstrip("/")
        rels[rel.attrib.get("Id")] = target

    output = {}

    for sheet in wb.iter(f"{{{MAIN_NS}}}sheet"):
        rid = sheet.attrib.get(f"{{{REL_NS}}}id")
        name = sheet.attrib.get("name", "")
        if rid in rels:
            output[name] = rels[rid]

    return output


def _value(cell, shared):
    cell_type = cell.attrib.get("t")

    if cell_type == "inlineStr":
        return "".join(
            node.text or ""
            for node in cell.iter(
                f"{{{MAIN_NS}}}t"
            )
        )

    value_node = cell.find(f"{{{MAIN_NS}}}v")
    raw = (
        value_node.text or ""
        if value_node is not None
        else ""
    )

    if cell_type == "s" and raw:
        try:
            return shared[int(raw)]
        except (ValueError, IndexError):
            return raw

    return raw


def parse_legal_requirements(path):
    if not zipfile.is_zipfile(path):
        raise ValueError(
            "El archivo no es XLSX/XLSM válido."
        )

    with zipfile.ZipFile(path, "r") as zf:
        shared = _shared_strings(zf)
        paths = _sheet_paths(zf)

        sheet_path = (
            paths.get("Documentos")
            or next(iter(paths.values()))
        )

        root = ET.fromstring(
            zf.read(sheet_path)
        )

        rows = []

        for row in root.iter(f"{{{MAIN_NS}}}row"):
            row_number = int(
                row.attrib.get("r", "0") or 0
            )
            cells = {}

            for cell in row.findall(f"{{{MAIN_NS}}}c"):
                ref = cell.attrib.get("r", "")
                col = _col_number(ref)

                if col < 1 or col > 7:
                    continue

                value = str(
                    _value(cell, shared) or ""
                ).strip()

                cells[col] = value

            rows.append((row_number, cells))

    header_index = None

    for index, (_, cells) in enumerate(rows):
        if (
            cells.get(1, "").upper() == "N°"
            and "REQUISITO" in cells.get(2, "").upper()
            and "ESTADO" in cells.get(7, "").upper()
        ):
            header_index = index
            break

    if header_index is None:
        raise ValueError(
            "No se encontró la cabecera esperada "
            "del registro legal."
        )

    output = []

    for row_number, cells in rows[header_index + 1:]:
        raw_number = cells.get(1, "").strip()
        requirement = cells.get(2, "").strip()

        if not requirement:
            continue

        try:
            number = int(float(raw_number))
        except (ValueError, TypeError):
            continue

        output.append(
            {
                "source_row": row_number,
                "number": number,
                "requirement": requirement,
                "promulgated_by": cells.get(3, "").strip(),
                "location": cells.get(4, "").strip(),
                "responsible": cells.get(5, "").strip(),
                "interested_parties": cells.get(6, "").strip(),
                "status": cells.get(7, "").strip(),
            }
        )

    return output
