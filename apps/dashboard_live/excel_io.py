import io
import re
import zipfile
import xml.etree.ElementTree as ET
from collections import OrderedDict
from decimal import Decimal, InvalidOperation

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
ET.register_namespace("", MAIN_NS)
ET.register_namespace("r", REL_NS)


def normalize_target(target):
    if target.startswith("/"):
        return target.lstrip("/")
    if target.startswith("xl/"):
        return target
    return "xl/" + target.lstrip("/")


def clean_text(value):
    if value is None:
        return ""
    return " ".join(str(value).replace("\xa0", " ").split()).strip()


def decimal_or_none(value):
    text = clean_text(value)
    if not text or text == "-":
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def numeric_display(raw_value, indicator="", force_percent=False):
    number = decimal_or_none(raw_value)
    if number is None:
        return None, clean_text(raw_value), Decimal("1")
    scale = Decimal("1")
    display = number
    if force_percent or ("%" in clean_text(indicator) and abs(number) <= Decimal("1")):
        display = number * Decimal("100")
        scale = Decimal("0.01")
    return display, "", scale


class WorkbookReader:
    def __init__(self, path):
        self.path = path
        self.zf = zipfile.ZipFile(path, "r")
        self.shared = self._shared_strings()
        self.sheet_paths = self._sheet_paths()

    def close(self):
        self.zf.close()

    def _shared_strings(self):
        name = "xl/sharedStrings.xml"
        if name not in self.zf.namelist():
            return []
        root = ET.fromstring(self.zf.read(name))
        values = []
        for item in root.iter(f"{{{MAIN_NS}}}si"):
            values.append("".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t")))
        return values

    def _sheet_paths(self):
        workbook = ET.fromstring(self.zf.read("xl/workbook.xml"))
        relationships = ET.fromstring(self.zf.read("xl/_rels/workbook.xml.rels"))
        rel_map = {
            rel.attrib["Id"]: normalize_target(rel.attrib.get("Target", ""))
            for rel in relationships
        }
        output = OrderedDict()
        for sheet in workbook.iter(f"{{{MAIN_NS}}}sheet"):
            rid = sheet.attrib.get(f"{{{REL_NS}}}id")
            output[sheet.attrib["name"]] = rel_map[rid]
        return output

    def _value(self, cell):
        cell_type = cell.attrib.get("t")
        if cell_type == "inlineStr":
            return "".join(node.text or "" for node in cell.iter(f"{{{MAIN_NS}}}t"))
        value_node = cell.find(f"{{{MAIN_NS}}}v")
        raw = value_node.text or "" if value_node is not None else ""
        if cell_type == "s" and raw:
            try:
                return self.shared[int(raw)]
            except (ValueError, IndexError):
                return raw
        if cell_type == "b":
            return "TRUE" if raw == "1" else "FALSE"
        return raw

    def sheet(self, name):
        root = ET.fromstring(self.zf.read(self.sheet_paths[name]))
        cells = {}
        for cell in root.iter(f"{{{MAIN_NS}}}c"):
            ref = cell.attrib.get("r", "")
            formula_node = cell.find(f"{{{MAIN_NS}}}f")
            cells[ref] = {
                "value": self._value(cell),
                "formula": (formula_node.text or "") if formula_node is not None else "",
                "style": cell.attrib.get("s", ""),
            }
        return cells


def _set_inline_string(cell, value):
    for tag in (f"{{{MAIN_NS}}}f", f"{{{MAIN_NS}}}v", f"{{{MAIN_NS}}}is"):
        for child in list(cell.findall(tag)):
            cell.remove(child)
    cell.set("t", "inlineStr")
    inline = ET.SubElement(cell, f"{{{MAIN_NS}}}is")
    text = ET.SubElement(inline, f"{{{MAIN_NS}}}t")
    text.text = "" if value is None else str(value)


def _set_number(cell, value):
    for tag in (f"{{{MAIN_NS}}}f", f"{{{MAIN_NS}}}v", f"{{{MAIN_NS}}}is"):
        for child in list(cell.findall(tag)):
            cell.remove(child)
    cell.attrib.pop("t", None)
    value_node = ET.SubElement(cell, f"{{{MAIN_NS}}}v")
    value_node.text = str(value)


class WorkbookPatcher:
    def __init__(self, source_path):
        with zipfile.ZipFile(source_path, "r") as zf:
            self.files = {name: zf.read(name) for name in zf.namelist()}

        workbook = ET.fromstring(self.files["xl/workbook.xml"])
        relationships = ET.fromstring(self.files["xl/_rels/workbook.xml.rels"])
        rel_map = {
            rel.attrib["Id"]: normalize_target(rel.attrib.get("Target", ""))
            for rel in relationships
        }
        self.sheet_paths = {}
        for sheet in workbook.iter(f"{{{MAIN_NS}}}sheet"):
            rid = sheet.attrib.get(f"{{{REL_NS}}}id")
            self.sheet_paths[sheet.attrib["name"]] = rel_map[rid]
        self.sheet_roots = {}

    def _root(self, sheet_name):
        if sheet_name not in self.sheet_roots:
            path = self.sheet_paths[sheet_name]
            self.sheet_roots[sheet_name] = ET.fromstring(self.files[path])
        return self.sheet_roots[sheet_name]

    def _cell(self, sheet_name, ref):
        root = self._root(sheet_name)
        for cell in root.iter(f"{{{MAIN_NS}}}c"):
            if cell.attrib.get("r") == ref:
                return cell
        row_number = int(re.sub(r"[^0-9]", "", ref))
        sheet_data = root.find(f"{{{MAIN_NS}}}sheetData")
        row = None
        for candidate in sheet_data.findall(f"{{{MAIN_NS}}}row"):
            if int(candidate.attrib.get("r", "0")) == row_number:
                row = candidate
                break
        if row is None:
            row = ET.SubElement(sheet_data, f"{{{MAIN_NS}}}row", {"r": str(row_number)})
        return ET.SubElement(row, f"{{{MAIN_NS}}}c", {"r": ref})

    def string(self, sheet, ref, value):
        _set_inline_string(self._cell(sheet, ref), value)

    def number(self, sheet, ref, value):
        _set_number(self._cell(sheet, ref), value)

    def save_bytes(self):
        for sheet_name, root in self.sheet_roots.items():
            path = self.sheet_paths[sheet_name]
            self.files[path] = ET.tostring(root, encoding="utf-8", xml_declaration=True)

        workbook = ET.fromstring(self.files["xl/workbook.xml"])
        calc = workbook.find(f"{{{MAIN_NS}}}calcPr")
        if calc is None:
            calc = ET.SubElement(workbook, f"{{{MAIN_NS}}}calcPr")
        calc.set("calcMode", "auto")
        calc.set("fullCalcOnLoad", "1")
        calc.set("forceFullCalc", "1")
        self.files["xl/workbook.xml"] = ET.tostring(workbook, encoding="utf-8", xml_declaration=True)

        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name, data in self.files.items():
                zf.writestr(name, data)
        return output.getvalue()
