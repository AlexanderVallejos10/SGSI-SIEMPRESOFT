import hashlib
import mimetypes
import os
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from django.core.files import File as DjangoFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.controls.models import Control, ControlFramework
from apps.controls.models_iso import (
    ControlSupportReference,
    ISOClause,
    ISODataQualityIssue,
    ISOIssueSeverity,
    ISOIssueType,
    ISORequirement,
)
from apps.documents.models import SourceArtifact


FRAMEWORK_CODE = "ISO27001-2022"
FRAMEWORK_NAME = "ISO/IEC 27001"
FRAMEWORK_VERSION = "2022"

CLAUSE_SHEET = "CLAUSULAS 4-10"
SUPPORT_SHEET = "Opciones y Controles de Tratam."
CONTROL_SHEET = "Hoja2"

CONTROL_DOMAINS = {
    "5": "Controles organizacionales",
    "6": "Controles de personal",
    "7": "Controles físicos",
    "8": "Controles tecnológicos",
}

CLAUSE_CODE_RE = re.compile(r"^\d+(?:\.\d+)*\.?$")
CONTROL_CODE_RE = re.compile(r"^([5-8]\.\d+)\s+(.+)$")


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(
        ch for ch in value if not unicodedata.combining(ch)
    )
    return " ".join(value.casefold().split())


def normalized_clause_code(value):
    value = str(value or "").strip()
    return value[:-1] if value.endswith(".") else value


def normalized_control_code(value):
    """
    Corrige artefactos binarios de Excel solo cuando el XML expone
    un decimal largo (por ejemplo 5.0999999999999996 -> 5.1).

    Los códigos textuales como 5.10, 8.10, etc. se preservan tal cual.
    """
    value = str(value or "").strip()

    if re.fullmatch(r"[5-8]\.\d{8,}", value):
        value = f"{float(value):.2f}".rstrip("0").rstrip(".")

    return value


def model_choice_value(model, field_name, preferred_values):
    """
    Selecciona un valor válido según las choices reales del modelo actual.
    """
    field = model._meta.get_field(field_name)
    choice_values = [
        item[0]
        for item in (field.choices or [])
    ]

    for candidate in preferred_values:
        if candidate in choice_values:
            return candidate

    default = field.get_default()
    if default not in (None, ""):
        return default

    if choice_values:
        return choice_values[0]

    return ""


def sha256_file(path):
    digest = hashlib.sha256()
    size = 0
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def col_index(cell_ref):
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    value = 0
    for ch in letters:
        value = value * 26 + (ord(ch.upper()) - 64)
    return value


class SimpleXLSX:
    MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

    def __init__(self, path):
        self.path = path
        self.zip = zipfile.ZipFile(path, "r")
        self.shared_strings = self._load_shared_strings()
        self.sheet_paths = self._load_sheet_paths()

    def close(self):
        self.zip.close()

    def _load_shared_strings(self):
        name = "xl/sharedStrings.xml"
        if name not in self.zip.namelist():
            return []

        root = ET.fromstring(self.zip.read(name))
        values = []
        ns = {"m": self.MAIN_NS}

        for si in root.findall("m:si", ns):
            texts = [node.text or "" for node in si.iter(f"{{{self.MAIN_NS}}}t")]
            values.append("".join(texts))
        return values

    def _load_sheet_paths(self):
        wb_root = ET.fromstring(self.zip.read("xl/workbook.xml"))
        rel_root = ET.fromstring(
            self.zip.read("xl/_rels/workbook.xml.rels")
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

        ns = {
            "m": self.MAIN_NS,
            "r": self.REL_NS,
        }

        result = {}
        for sheet in wb_root.findall("m:sheets/m:sheet", ns):
            name = sheet.attrib["name"]
            rid = sheet.attrib[f"{{{self.REL_NS}}}id"]
            result[name] = rels[rid]
        return result

    def rows(self, sheet_name):
        path = self.sheet_paths.get(sheet_name)
        if not path:
            raise CommandError(
                f"No existe la hoja requerida: {sheet_name}"
            )

        root = ET.fromstring(self.zip.read(path))
        ns = {"m": self.MAIN_NS}
        output = []

        for row in root.findall(".//m:sheetData/m:row", ns):
            row_num = int(row.attrib.get("r", len(output) + 1))
            cells = {}

            for cell in row.findall("m:c", ns):
                ref = cell.attrib.get("r", "")
                idx = col_index(ref)
                cell_type = cell.attrib.get("t")
                value = ""

                if cell_type == "inlineStr":
                    texts = [
                        node.text or ""
                        for node in cell.iter(f"{{{self.MAIN_NS}}}t")
                    ]
                    value = "".join(texts)
                else:
                    v = cell.find("m:v", ns)
                    raw = "" if v is None else (v.text or "")

                    if cell_type == "s" and raw:
                        try:
                            value = self.shared_strings[int(raw)]
                        except Exception:
                            value = raw
                    else:
                        value = raw

                cells[idx] = value

            output.append((row_num, cells))

        return output


def make_issue_code(source_sha, issue_type, sheet, row, marker):
    raw = f"{source_sha}|{issue_type}|{sheet}|{row}|{marker}"
    return "ISOISS-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20].upper()


def register_issue(
    source_sha,
    artifact,
    issue_type,
    severity,
    description,
    sheet="",
    row=None,
    marker="",
    apply_changes=False,
):
    if not apply_changes:
        return

    code = make_issue_code(
        source_sha,
        issue_type,
        sheet,
        row or 0,
        marker,
    )

    ISODataQualityIssue.objects.update_or_create(
        code=code,
        defaults={
            "issue_type": issue_type,
            "severity": severity,
            "description": description,
            "source_artifact": artifact,
            "source_sheet": sheet,
            "source_row": row,
            "resolved": False,
        },
    )


def ensure_source_artifact(path, checksum, size, apply_changes):
    filename = os.path.basename(path)
    code = "SRC-ISO-" + checksum[:20].upper()

    if not apply_changes:
        return None, code

    source_kind = model_choice_value(
        SourceArtifact,
        "source_kind",
        (
            "standalone",
            "uploaded",
            "upload",
            "manual",
            "file",
            "zip_member",
        ),
    )
    quality_status = model_choice_value(
        SourceArtifact,
        "quality_status",
        (
            "verified",
            "warning",
            "pending",
        ),
    )

    artifact, _ = SourceArtifact.objects.update_or_create(
        code=code,
        defaults={
            "original_name": filename,
            "original_path": filename,
            "source_archive": "",
            "source_kind": source_kind,
            "extension": Path(filename).suffix.lower().lstrip("."),
            "mime_type": (
                mimetypes.guess_type(filename)[0]
                or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            "size_bytes": size,
            "checksum_sha256": checksum,
            "source_verified": True,
            "quality_status": quality_status,
            "quality_notes": (
                "Fuente independiente registrada por import_iso_verification."
            ),
        },
    )

    if not artifact.file:
        storage_name = f"{code}_{filename}"
        with open(path, "rb") as handle:
            artifact.file.save(
                storage_name,
                DjangoFile(handle),
                save=False,
            )
        artifact.save(update_fields=("file", "updated_at"))

    return artifact, code


def parse_canonical_controls(rows):
    controls = {}
    for row_num, cells in rows:
        pairs = (
            (1, 2),
            (4, 5),
            (7, 8),
        )
        for code_col, name_col in pairs:
            code = normalized_control_code(
                cells.get(code_col, "")
            )
            name = str(cells.get(name_col, "") or "").strip()

            if re.fullmatch(r"[5-8]\.\d+", code) and name:
                controls[code] = {
                    "code": code,
                    "name": name,
                    "domain": CONTROL_DOMAINS[code.split(".")[0]],
                    "source_row": row_num,
                }

    return controls


class Command(BaseCommand):
    help = (
        "Importa VerificacionNorma.xlsx como estructura ISO 27001:2022: "
        "cláusulas 4-10, requisitos, 93 controles Anexo A y referencias "
        "documentales. Por defecto es PREVIEW; use --apply para guardar."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "xlsx_path",
            help=(
                "Ruta del Excel dentro del contenedor. "
                "Ejemplo: /app/imports/VerificacionNorma.xlsx"
            ),
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Guarda los datos importados.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        path = os.path.abspath(options["xlsx_path"])
        apply_changes = options["apply"]

        if not os.path.isfile(path):
            raise CommandError(f"No existe el archivo: {path}")
        if not zipfile.is_zipfile(path):
            raise CommandError(f"No es un XLSX/ZIP válido: {path}")

        checksum, size = sha256_file(path)
        artifact, source_code = ensure_source_artifact(
            path,
            checksum,
            size,
            apply_changes,
        )

        workbook = SimpleXLSX(path)
        try:
            clause_rows = workbook.rows(CLAUSE_SHEET)
            support_rows = workbook.rows(SUPPORT_SHEET)
            control_rows = workbook.rows(CONTROL_SHEET)
        finally:
            workbook.close()

        canonical_controls = parse_canonical_controls(control_rows)

        if len(canonical_controls) != 93:
            raise CommandError(
                "La hoja Hoja2 no produjo exactamente 93 controles "
                f"canónicos. Detectados: {len(canonical_controls)}"
            )

        framework = None
        if apply_changes:
            framework, _ = ControlFramework.objects.update_or_create(
                code=FRAMEWORK_CODE,
                defaults={
                    "name": FRAMEWORK_NAME,
                    "version": FRAMEWORK_VERSION,
                    "active": True,
                },
            )

        clauses_preview = []
        requirements_preview = []
        current_clause_code = None

        for row_num, cells in clause_rows:
            label = str(cells.get(1, "") or "").strip()
            description = str(cells.get(2, "") or "").strip()
            support = str(cells.get(3, "") or "").strip()

            if not description:
                continue

            is_heading = bool(CLAUSE_CODE_RE.fullmatch(label))
            clause_code = current_clause_code

            if is_heading:
                clause_code = normalized_clause_code(label)
                current_clause_code = clause_code
                clauses_preview.append(
                    (clause_code, description, row_num)
                )

            if current_clause_code:
                requirements_preview.append(
                    {
                        "clause_code": current_clause_code,
                        "source_label": label,
                        "description": description,
                        "supporting_reference": support,
                        "is_clause_heading": is_heading,
                        "source_row": row_num,
                    }
                )

        if apply_changes:
            clause_objects = {}

            for code, title, row_num in clauses_preview:
                parent_code = (
                    code.rsplit(".", 1)[0]
                    if "." in code
                    else None
                )
                parent = clause_objects.get(parent_code)

                clause, _ = ISOClause.objects.update_or_create(
                    framework=framework,
                    code=code,
                    defaults={
                        "title": title,
                        "parent": parent,
                        "level": code.count(".") + 1,
                        "source_artifact": artifact,
                        "source_sheet": CLAUSE_SHEET,
                        "source_row": row_num,
                        "active": True,
                    },
                )
                clause_objects[code] = clause

            for item in requirements_preview:
                clause = clause_objects[item["clause_code"]]
                ISORequirement.objects.update_or_create(
                    source_artifact=artifact,
                    source_sheet=CLAUSE_SHEET,
                    source_row=item["source_row"],
                    defaults={
                        "clause": clause,
                        "source_label": item["source_label"][:30],
                        "description": item["description"],
                        "supporting_reference": item["supporting_reference"],
                        "is_clause_heading": item["is_clause_heading"],
                    },
                )

        control_objects = {}
        if apply_changes:
            for code, data in canonical_controls.items():
                control, _ = Control.objects.update_or_create(
                    framework=framework,
                    code=code,
                    defaults={
                        "name": data["name"][:255],
                        "domain": data["domain"][:120],
                    },
                )
                control_objects[code] = control

        normalized_name_to_code = {}
        for code, data in canonical_controls.items():
            normalized_name_to_code.setdefault(
                normalize(data["name"]),
                [],
            ).append(code)

        support_matches = []
        unmatched_support = []
        support_discrepancies = []

        for row_num, cells in support_rows:
            raw = str(cells.get(2, "") or "").strip()
            support = str(cells.get(3, "") or "").strip()

            match = CONTROL_CODE_RE.fullmatch(raw)
            if not match:
                continue

            raw_code = match.group(1)
            raw_name = match.group(2).strip()
            canonical_code = None

            if raw_code in canonical_controls:
                canonical_code = raw_code
            else:
                candidates = normalized_name_to_code.get(
                    normalize(raw_name),
                    [],
                )
                if len(candidates) == 1:
                    canonical_code = candidates[0]
                    support_discrepancies.append(
                        (
                            row_num,
                            raw_code,
                            raw_name,
                            canonical_code,
                        )
                    )
                else:
                    unmatched_support.append(
                        (row_num, raw_code, raw_name)
                    )
                    continue

            support_matches.append(
                {
                    "row_num": row_num,
                    "raw_code": raw_code,
                    "raw_name": raw_name,
                    "canonical_code": canonical_code,
                    "support": support,
                }
            )

        if apply_changes:
            for item in support_matches:
                control = control_objects[item["canonical_code"]]
                ControlSupportReference.objects.update_or_create(
                    control=control,
                    source_artifact=artifact,
                    source_sheet=SUPPORT_SHEET,
                    source_row=item["row_num"],
                    defaults={
                        "supporting_reference": item["support"],
                        "raw_control_code": item["raw_code"],
                        "raw_control_name": item["raw_name"][:255],
                    },
                )

            for row_num, raw_code, raw_name, canonical_code in support_discrepancies:
                register_issue(
                    checksum,
                    artifact,
                    ISOIssueType.SOURCE_DISCREPANCY,
                    ISOIssueSeverity.WARNING,
                    (
                        f"La fuente usa el código {raw_code} para "
                        f"'{raw_name}', pero el listado canónico de 93 "
                        f"controles de Hoja2 lo identifica como {canonical_code}. "
                        "Se conservó el valor original y se vinculó por nombre."
                    ),
                    SUPPORT_SHEET,
                    row_num,
                    f"{raw_code}->{canonical_code}",
                    True,
                )

            for row_num, raw_code, raw_name in unmatched_support:
                register_issue(
                    checksum,
                    artifact,
                    ISOIssueType.UNMATCHED_CONTROL,
                    ISOIssueSeverity.ERROR,
                    (
                        f"No fue posible conciliar el control de la fuente: "
                        f"{raw_code} {raw_name}"
                    ),
                    SUPPORT_SHEET,
                    row_num,
                    raw_code,
                    True,
                )

            # Discrepancia conocida entre el libro y la estructura 2022
            # usada por el Manual SGSI del proyecto. No se corrige en silencio.
            for code, expected_keyword in (
                ("10.1", "mejora"),
                ("10.2", "no conform"),
            ):
                clause = next(
                    (
                        (c, title, row)
                        for c, title, row in clauses_preview
                        if c == code
                    ),
                    None,
                )
                if clause and expected_keyword not in normalize(clause[1]):
                    register_issue(
                        checksum,
                        artifact,
                        ISOIssueType.CLAUSE_MAPPING,
                        ISOIssueSeverity.WARNING,
                        (
                            f"La hoja '{CLAUSE_SHEET}' rotula la cláusula "
                            f"{code} como '{clause[1]}'. Se conserva la fuente "
                            "sin corregirla; requiere revisión frente a la "
                            "estructura 2022 utilizada por el Manual SGSI."
                        ),
                        CLAUSE_SHEET,
                        clause[2],
                        code,
                        True,
                    )

        self.stdout.write("=== IMPORTACIÓN ISO 27001:2022 ===")
        self.stdout.write(
            f"Modo: {'APPLY' if apply_changes else 'PREVIEW'}"
        )
        self.stdout.write(
            f"Fuente: {os.path.basename(path)}"
        )
        self.stdout.write(
            f"SourceArtifact: {source_code}"
        )
        self.stdout.write(
            f"SHA-256: {checksum}"
        )
        source_kind_preview = model_choice_value(
            SourceArtifact,
            "source_kind",
            (
                "standalone",
                "uploaded",
                "upload",
                "manual",
                "file",
                "zip_member",
            ),
        )
        quality_status_preview = model_choice_value(
            SourceArtifact,
            "quality_status",
            (
                "verified",
                "warning",
                "pending",
            ),
        )
        self.stdout.write(
            f"source_kind seleccionado: {source_kind_preview}"
        )
        self.stdout.write(
            f"quality_status seleccionado: {quality_status_preview}"
        )
        self.stdout.write("")
        self.stdout.write(
            f"Cláusulas detectadas: {len(clauses_preview)}"
        )
        self.stdout.write(
            f"Filas/requisitos importables: {len(requirements_preview)}"
        )
        self.stdout.write(
            f"Controles canónicos Hoja2: {len(canonical_controls)}"
        )
        self.stdout.write(
            f"Filas de soporte conciliadas: {len(support_matches)}"
        )
        self.stdout.write(
            f"Discrepancias de código conciliadas por nombre: "
            f"{len(support_discrepancies)}"
        )
        self.stdout.write(
            f"Filas de soporte no conciliadas: {len(unmatched_support)}"
        )

        if support_discrepancies:
            self.stdout.write("")
            self.stdout.write("=== DISCREPANCIAS ===")
            for row_num, raw_code, raw_name, canonical_code in support_discrepancies:
                self.stdout.write(
                    f"Fila {row_num}: {raw_code} '{raw_name}' "
                    f"→ canónico {canonical_code}"
                )

        if unmatched_support:
            self.stdout.write("")
            self.stdout.write("=== NO CONCILIADOS ===")
            for row_num, raw_code, raw_name in unmatched_support:
                self.stdout.write(
                    f"Fila {row_num}: {raw_code} '{raw_name}'"
                )

        if not apply_changes:
            transaction.set_rollback(True)
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "PREVIEW: no se modificó PostgreSQL ni el storage."
                )
            )
        else:
            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    "Importación ISO 27001:2022 finalizada."
                )
            )
