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


def _clean(value):
    if value is None:
        return ""
    return " ".join(
        str(value)
        .replace("\xa0", " ")
        .split()
    ).strip()


def _column_number(cell_ref):
    letters = "".join(
        ch for ch in cell_ref
        if ch.isalpha()
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

    values = []

    for item in root.iter(
        f"{{{MAIN_NS}}}si"
    ):
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
    workbook = ET.fromstring(
        zf.read(
            "xl/workbook.xml"
        )
    )

    relationships = ET.fromstring(
        zf.read(
            "xl/_rels/workbook.xml.rels"
        )
    )

    rel_map = {}

    for rel in relationships:
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

        rel_map[
            rel.attrib.get("Id")
        ] = target

    output = {}

    for sheet in workbook.iter(
        f"{{{MAIN_NS}}}sheet"
    ):
        rid = sheet.attrib.get(
            f"{{{REL_NS}}}id"
        )
        name = sheet.attrib.get(
            "name",
            "",
        )

        if rid in rel_map:
            output[name] = (
                rel_map[rid]
            )

    return output


def _cell_value(
    cell,
    shared,
):
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

    if (
        cell_type == "s"
        and raw
    ):
        try:
            return shared[
                int(raw)
            ]
        except (
            ValueError,
            IndexError,
        ):
            return raw

    return raw


def _read_sheet(
    file_path,
    sheet_name=None,
):
    if not zipfile.is_zipfile(
        file_path
    ):
        raise ValueError(
            "El archivo no es un XLSX/XLSM válido."
        )

    with zipfile.ZipFile(
        file_path,
        "r",
    ) as zf:
        shared = _shared_strings(
            zf
        )

        paths = _sheet_paths(
            zf
        )

        if sheet_name:
            sheet_path = paths.get(
                sheet_name
            )

            if not sheet_path:
                raise ValueError(
                    f"No se encontró la hoja {sheet_name!r}."
                )
        else:
            if not paths:
                raise ValueError(
                    "El Excel no contiene hojas."
                )

            sheet_path = next(
                iter(
                    paths.values()
                )
            )

        root = ET.fromstring(
            zf.read(
                sheet_path
            )
        )

        rows = []

        for row in root.iter(
            f"{{{MAIN_NS}}}row"
        ):
            row_number = int(
                row.attrib.get(
                    "r",
                    "0",
                )
                or 0
            )

            cells = {}

            for cell in row.findall(
                f"{{{MAIN_NS}}}c"
            ):
                column = (
                    _column_number(
                        cell.attrib.get(
                            "r",
                            "",
                        )
                    )
                )

                if not column:
                    continue

                cells[column] = (
                    _cell_value(
                        cell,
                        shared,
                    )
                )

            rows.append(
                (
                    row_number,
                    cells,
                )
            )

        return rows


def parse_interested_parties(
    file_path,
):
    rows = _read_sheet(
        file_path
    )

    start_index = None

    for index, (
        _,
        cells,
    ) in enumerate(
        rows
    ):
        first = _clean(
            cells.get(1)
        ).upper()

        second = _clean(
            cells.get(2)
        ).upper()

        if (
            "PARTE INTERESADA"
            in first
            and "NECESIDADES"
            in second
        ):
            start_index = (
                index + 1
            )
            break

    if start_index is None:
        raise ValueError(
            "No se encontró la cabecera "
            "PARTE INTERESADA / NECESIDADES."
        )

    output = []
    current_party = ""

    for (
        row_number,
        cells,
    ) in rows[
        start_index:
    ]:
        party = _clean(
            cells.get(1)
        )
        need = _clean(
            cells.get(2)
        )
        expectation = _clean(
            cells.get(3)
        )

        if (
            party.startswith(
                "El contenido de este documento"
            )
            or need.startswith(
                "El contenido de este documento"
            )
        ):
            break

        if party:
            current_party = party

        if (
            current_party
            and (
                need
                or expectation
            )
        ):
            output.append(
                {
                    "source_row":
                        row_number,
                    "party_name":
                        current_party,
                    "need":
                        need,
                    "expectation":
                        expectation,
                }
            )

    return output


def parse_legal_requirements(
    file_path,
):
    rows = _read_sheet(
        file_path,
        sheet_name="Documentos",
    )

    start_index = None

    for index, (
        _,
        cells,
    ) in enumerate(
        rows
    ):
        first = _clean(
            cells.get(1)
        ).upper()
        second = _clean(
            cells.get(2)
        ).upper()

        if (
            first
            in {
                "N°",
                "Nº",
                "N",
            }
            and "REQUISITO"
            in second
        ):
            start_index = (
                index + 1
            )
            break

    if start_index is None:
        raise ValueError(
            "No se encontró la cabecera "
            "del registro legal."
        )

    output = []

    for (
        row_number,
        cells,
    ) in rows[
        start_index:
    ]:
        item_no = _clean(
            cells.get(1)
        )
        requirement = _clean(
            cells.get(2)
        )
        promulgated_by = _clean(
            cells.get(3)
        )
        location = _clean(
            cells.get(4)
        )
        responsible = _clean(
            cells.get(5)
        )
        stakeholders = _clean(
            cells.get(6)
        )
        status = _clean(
            cells.get(7)
        )

        if not any(
            [
                item_no,
                requirement,
                promulgated_by,
                location,
                responsible,
                stakeholders,
                status,
            ]
        ):
            continue

        if (
            not item_no
            and not requirement
        ):
            continue

        output.append(
            {
                "source_row":
                    row_number,
                "item_no":
                    item_no,
                "requirement":
                    requirement,
                "promulgated_by":
                    promulgated_by,
                "location":
                    location,
                "responsible":
                    responsible,
                "stakeholders":
                    stakeholders,
                "status":
                    status,
            }
        )

    return output
