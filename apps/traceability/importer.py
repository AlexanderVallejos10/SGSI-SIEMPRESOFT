"""Explicit workbook ingestion. Exact matches only; preserve unresolved source rows."""

import difflib
import hashlib
import re
import unicodedata
from datetime import date, datetime
from io import BytesIO
from zipfile import BadZipFile, ZipFile

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from openpyxl import load_workbook

from apps.documents.models import Document
from apps.organization.models import Position
from apps.controls.models import Control
from apps.processes.models import ProcessNode
from apps.risks.models import (
    ANNEX_A_FRAMEWORK,
    IdentificationType,
    Risk,
    RiskAssessment,
    RiskTreatment,
    TreatmentOption,
)

from .models import DocumentLink, ImportBatch, SourceRow


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or "")).casefold()
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in value if not unicodedata.combining(c))).strip()


def unique_match(objects, value, label):
    key = normalize(value)
    matches = [o for o in objects if normalize(label(o)) == key] if key else []
    return matches[0] if len(matches) == 1 else None


def valid_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%d/%m/%Y").date()
    except ValueError:
        return None


def number(value, maximum):
    m = re.match(r"^([1-9])(?:\s|$)", str(value or ""))
    n = int(m[1]) if m else None
    return n if n and n <= maximum else None


# Columnas por encabezado (fila 4), no por posición: la matriz 2026 y la matriz modelo
# de Karim tienen distinto número y orden de columnas.
RISK_COLUMNS = (
    ("code", ("id",), True),
    ("process", ("proceso",), False),
    ("origin", ("origen del riesgo",), False),
    ("category", ("categoria de riesgo",), False),
    ("threat", ("fuente de riesgo",), False),
    ("event", ("evento",), False),
    ("motivation", ("estado final deseado",), False),
    ("affected_asset_text", ("activo o proceso de negocio afectado", "activo afectado"), False),
    ("scenario", ("escenario estrategico",), False),
    ("operational_scenario", ("escenario operacional",), False),
    ("finding_origin", ("origen del hallazgo",), False),
    ("evidence_reference", ("referencia",), False),
    ("impact", ("consecuencia",), True),
    ("probability", ("probabilidad",), True),
    ("existing_controls", ("controles existentes",), False),
    ("owner", ("propietario del riesgo",), False),
    ("identification_type", ("tipo de identificacion",), False),
    ("project_name", ("proyecto",), True),
)
TREATMENT_COLUMNS = (
    ("risk_code", ("id del riesgo",), False),
    ("option", ("opcion de tratamiento",), False),
    ("control", ("control anexo a", "control del anexo a", "control iso"), False),
    ("action", ("control actividad a implementar", "actividad a implementar"), False),
    ("responsible", ("responsable de implementacion",), False),
    ("start", ("plazo inicio",), False),
    ("end", ("plazo fin",), False),
    ("resources", ("recursos requeridos",), False),
    ("status", ("estado de implementacion",), False),
    ("residual_impact", ("consecuencia residual",), False),
    ("residual_probability", ("probabilidad residual",), False),
    ("closed", ("fecha de cierre",), False),
    ("notes", ("observaciones",), False),
    ("third_party_responsibilities", ("responsabilidades del tercero",), False),
    ("third_party", ("tercero",), False),
    ("contract_reference", ("contrato",), False),
    ("avoidance_method", ("como se evita", "forma de evitar"), False),
    ("acceptance_justification", ("justificacion",), False),
)
TEXT_FIELDS = (
    "process",
    "origin",
    "category",
    "threat",
    "event",
    "motivation",
    "affected_asset_text",
    "scenario",
    "operational_scenario",
    "finding_origin",
    "evidence_reference",
    "existing_controls",
    "project_name",
)
FIELD_LABELS = {
    "process": "proceso",
    "origin": "origen",
    "category": "categoría",
    "threat": "fuente",
    "event": "evento",
    "motivation": "motivación",
    "affected_asset_text": "activo afectado",
    "scenario": "escenario estratégico",
    "operational_scenario": "escenario operacional",
    "finding_origin": "origen del hallazgo",
    "evidence_reference": "referencia",
    "existing_controls": "controles existentes",
    "project_name": "proyecto",
}
CONTROL_CODE = re.compile(r"^\s*(?:A\s*\.?\s*)?([5-8]\.\d{1,2})\b", re.IGNORECASE)


def header_map(header, columns):
    """Devuelve {campo: índice}. `exact` exige igualdad para encabezados muy cortos."""
    found = {}
    for index, cell in enumerate(header):
        key = normalize(cell)
        if not key:
            continue
        for field, prefixes, exact in columns:
            if field in found:
                continue
            if any(key == p or (not exact and key.startswith(p + " ")) for p in prefixes):
                found[field] = index
                break
    return found


def cell(values, columns, field):
    index = columns.get(field)
    value = values[index] if index is not None and index < len(values) else None
    if isinstance(value, str) and value.startswith("="):
        return None  # fórmula sin valor calculado
    return value


def text(value):
    return "" if value is None else str(value).strip()


def resolve_processes(source, processes):
    """Procesos del mapa para el texto de la fuente, y una observación si algo requiere revisión."""
    key = normalize(source)
    if not key:
        return [], "Proceso por vincular: sin dato"
    if key == "ambos":
        ose = [p for p in processes if p.code == "PROC-OSE"]
        note = "«Ambos» (PSE y OSE): el mapa V0.15 no tiene nodo PSE; "
        return ose, note + ("se vinculó solo a OSE." if ose else "vincular manualmente.")
    exact = [p for p in processes if normalize(p.name) == key or normalize(p.code) == key]
    if len(exact) == 1:
        return exact, ""
    by_name = {normalize(p.name): p for p in processes}
    close = difflib.get_close_matches(key, list(by_name), n=2, cutoff=0.9)
    if len(close) == 1:
        match = by_name[close[0]]
        return [match], f"Proceso «{source}» vinculado por similitud a «{match.name}»; confirmar."
    return [], "Proceso por vincular: " + text(source)


def treatment_option(value):
    key = normalize(value)
    by_number = {option.value[0]: option.value for option in TreatmentOption}
    if key[:1] in by_number:
        return by_number[key[:1]]
    for word, option in (
        ("transfer", TreatmentOption.TRANSFER),
        ("evit", TreatmentOption.AVOID),
        ("acept", TreatmentOption.ACCEPT),
        ("control", TreatmentOption.CONTROLS),
    ):
        if word in key:
            return option.value
    return text(value)[:60]


def identification(value):
    key = normalize(value)
    if "activo" in key:
        return IdentificationType.ASSETS
    if "proyecto" in key:
        return IdentificationType.PROJECT
    return IdentificationType.EVENTS


def annex_control(*values):
    for value in values:
        match = CONTROL_CODE.match(text(value))
        if match:
            control = Control.objects.filter(framework__code=ANNEX_A_FRAMEWORK, code=match[1]).first()
            if control:
                return control
    return None


@transaction.atomic
def import_workbook(uploaded, kind, actor, apply=False):
    data = uploaded.read()
    uploaded.seek(0)
    digest = hashlib.sha256(data).hexdigest()
    existing = ImportBatch.objects.filter(checksum=digest).first()
    if existing:
        return {
            "duplicate": True,
            "rows": existing.rows.count(),
            "issues": existing.rows.exclude(issue="").count(),
        }
    try:
        with ZipFile(BytesIO(data)) as archive:
            if sum(i.file_size for i in archive.infolist()) > 80 * 1024 * 1024:
                raise ValidationError("El archivo descomprimido supera el límite permitido.")
        workbook = load_workbook(BytesIO(data), read_only=True, data_only=False)
    except (BadZipFile, KeyError, ValueError) as exc:
        raise ValidationError("No se pudo leer el archivo XLSX.") from exc
    expected = {
        "risks": {"Matriz de riesgos", "Tratamiento de riesgos"},
        "owners": {"Documentos", "Instructivos", "Registros"},
        "access": {"Documentos", "Instructivos", "Registros"},
    }
    if kind not in expected or not expected[kind].issubset(workbook.sheetnames):
        raise ValidationError("Las hojas no corresponden al tipo de archivo seleccionado.")
    batch = ImportBatch.objects.create(
        name=uploaded.name, checksum=digest, kind=kind, created_by=actor, updated_by=actor
    )
    users = list(get_user_model().objects.all())
    positions = list(Position.objects.filter(is_active=True))
    processes = list(ProcessNode.objects.filter(is_active=True))
    documents = list(Document.objects.all())

    def user_match(v):
        return unique_match(users, v, lambda u: u.get_full_name())

    def position_match(v):
        return unique_match(positions, v, lambda p: p.title)

    count = issues = 0
    summary = {"created": 0, "updated": 0, "unchanged": 0, "skipped_empty": 0}
    changes = []
    # La matriz siempre antes que el tratamiento: el tratamiento busca el riesgo por su ID.
    order = ["Matriz de riesgos", "Tratamiento de riesgos"] if kind == "risks" else workbook.sheetnames
    for sheet in (workbook[name] for name in order):
        if sheet.title not in expected[kind]:
            continue
        if sheet.max_row > 10000 or sheet.max_column > 100:
            raise ValidationError("La hoja excede el tamaño admitido.")
        columns = None
        for index, values in enumerate(sheet.iter_rows(values_only=True), 1):
            v = list(values) + [None] * 20
            row_kind = kind
            if kind == "risks":
                spec = RISK_COLUMNS if sheet.title == "Matriz de riesgos" else TREATMENT_COLUMNS
                key_field = "code" if sheet.title == "Matriz de riesgos" else "risk_code"
                if columns is None:
                    found = header_map(values, spec)
                    if key_field in found and index <= 10:
                        columns = found
                    elif index > 10:
                        raise ValidationError(
                            f"No se encontró la fila de encabezados en la hoja «{sheet.title}»."
                        )
                    continue
                code = text(cell(v, columns, key_field))
                if not re.fullmatch(r"R[0-9]+", code):
                    continue
                if sheet.title == "Matriz de riesgos" and not any(
                    text(cell(v, columns, f)) for f in ("process", "threat", "event")
                ):
                    summary["skipped_empty"] += 1  # fila en blanco con ID pre-generado
                    continue
            else:
                row_kind = "owners" if kind == "owners" or sheet.title == "Registros" else "access"
                if index < (5 if row_kind == "owners" else 4) or not v[1]:
                    continue
            raw = [x.isoformat() if isinstance(x, (date, datetime)) else x for x in values]
            row = SourceRow.objects.create(
                batch=batch,
                sheet=sheet.title,
                row_number=index,
                values=raw,
                created_by=actor,
                updated_by=actor,
            )
            problems = []
            if kind == "risks" and sheet.title == "Matriz de riesgos":
                data = {f: text(cell(v, columns, f)) for f in TEXT_FIELDS}
                data["scenario"] = data["scenario"] or data["event"] or "Pendiente"
                for field in TEXT_FIELDS:
                    limit = getattr(Risk._meta.get_field(field), "max_length", None)
                    if limit and len(data[field]) > limit:
                        problems.append(
                            f"{FIELD_LABELS[field].capitalize()} recortado ({len(data[field])} caracteres); "
                            "el texto completo queda en la fila original."
                        )
                        data[field] = data[field][: limit - 1] + "…"
                if "identification_type" in columns:
                    id_type = identification(cell(v, columns, "identification_type"))
                elif normalize(data["finding_origin"]) == "proyecto":
                    id_type = IdentificationType.PROJECT
                else:
                    id_type = IdentificationType.EVENTS
                owner_source = cell(v, columns, "owner")
                owner_user, owner_pos = user_match(owner_source), position_match(owner_source)
                probability = number(cell(v, columns, "probability"), 4)
                impact = number(cell(v, columns, "impact"), 5)
                new_nodes, process_note = resolve_processes(data["process"], processes)
                if process_note:
                    problems.append(process_note)

                risk = Risk.objects.filter(code=code).first()
                if risk:
                    diffs = []
                    old_process = risk.process
                    for field in TEXT_FIELDS:
                        new = data[field]
                        if new and new != getattr(risk, field):
                            diffs.append(f"{FIELD_LABELS[field]}: «{getattr(risk, field) or '—'}» → «{new}»")
                            setattr(risk, field, new)
                    if id_type != IdentificationType.EVENTS and risk.identification_type != id_type:
                        diffs.append(f"tipo: {risk.get_identification_type_display()} → {id_type.label}")
                        risk.identification_type = id_type
                    if owner_user and risk.owner_id != owner_user.pk:
                        risk.owner = owner_user
                        diffs.append(f"propietario → {owner_user.get_full_name()}")
                    if owner_pos and risk.owner_position_id != owner_pos.pk:
                        risk.owner_position = owner_pos
                        diffs.append(f"cargo propietario → {owner_pos.title}")
                    if diffs:
                        risk.updated_by = actor
                        risk.save()
                        if normalize(old_process) != normalize(risk.process):
                            old_nodes, _ = resolve_processes(old_process, processes)
                            stale = [n for n in old_nodes if n not in new_nodes]
                            if stale:
                                risk.processes.remove(*stale)
                        summary["updated"] += 1
                        problems.append("Actualizado desde esta fuente: " + "; ".join(diffs))
                        changes.append(f"{code}: " + "; ".join(diffs))
                    else:
                        summary["unchanged"] += 1
                else:
                    risk = Risk.objects.create(
                        code=code,
                        identification_type=id_type,
                        owner_position=owner_pos,
                        owner=owner_user,
                        created_by=actor,
                        updated_by=actor,
                        **data,
                    )
                    summary["created"] += 1
                if new_nodes:
                    risk.processes.add(*new_nodes)
                latest = risk.assessments.first()
                if probability and impact:
                    if not latest or (latest.probability, latest.impact) != (probability, impact):
                        RiskAssessment.objects.create(
                            risk=risk,
                            assessed_at=timezone.now(),
                            probability=probability,
                            impact=impact,
                            inherent_score=probability * impact,
                            notes="Importación: fecha técnica de carga, no fecha original de evaluación. Nivel cualitativo calculado con tabla 5x4.",
                            created_by=actor,
                            updated_by=actor,
                        )
                        if latest:
                            problems.append(
                                f"Nueva evaluación P{probability}×C{impact} (antes P{latest.probability}×C{latest.impact}); se conserva el historial."
                            )
                elif not latest:
                    problems.append("Evaluación incompleta")
                if risk.identification_type == IdentificationType.PROJECT and not risk.project_name:
                    problems.append("Riesgo de proyecto sin nombre de proyecto.")
                if not risk.owner_id and not risk.owner_position_id:
                    problems.append("Propietario por vincular: " + (text(owner_source) or "sin dato"))
                row.risk = risk
            elif kind == "risks":
                risk = Risk.objects.filter(code=code).first()
                row.risk = risk
                if risk:
                    action_source = cell(v, columns, "action")
                    control = annex_control(cell(v, columns, "control"), action_source)
                    extra = {
                        f: text(cell(v, columns, f))
                        for f in (
                            "third_party",
                            "third_party_responsibilities",
                            "contract_reference",
                            "avoidance_method",
                            "acceptance_justification",
                        )
                    }
                    # Un mismo archivo repetido nunca duplica acciones de tratamiento.
                    treatment, created = RiskTreatment.objects.get_or_create(
                        risk=risk,
                        action=text(action_source) or "Pendiente",
                        defaults={
                            "option": treatment_option(cell(v, columns, "option")),
                            "control": control,
                            "responsible": user_match(cell(v, columns, "responsible")),
                            "start_date": valid_date(cell(v, columns, "start")),
                            "due_date": valid_date(cell(v, columns, "end")),
                            "source_start": text(cell(v, columns, "start"))[:100],
                            "source_end": text(cell(v, columns, "end"))[:100],
                            "resources": text(cell(v, columns, "resources")),
                            "status": text(cell(v, columns, "status"))[:30] or "pending",
                            "residual_impact": number(cell(v, columns, "residual_impact"), 5),
                            "residual_probability": number(cell(v, columns, "residual_probability"), 4),
                            "closed_date": valid_date(cell(v, columns, "closed")),
                            "notes": text(cell(v, columns, "notes")),
                            "created_by": actor,
                            "updated_by": actor,
                            **extra,
                        },
                    )
                    if not created:
                        filled = []
                        if control and not treatment.control_id:
                            treatment.control = control
                            filled.append("control")
                        for field, value in extra.items():
                            if value and not getattr(treatment, field):
                                setattr(treatment, field, value)
                                filled.append(field)
                        if filled:
                            treatment.updated_by = actor
                            treatment.save()
                            problems.append("Tratamiento existente: se completaron campos vacíos.")
                        else:
                            problems.append("Tratamiento existente: no se sobrescribió.")
                    problems.extend(treatment.missing_requirements().values())
                    if not treatment.responsible_id:
                        problems.append("Responsable por vincular: " + text(cell(v, columns, "responsible")))
                    if not treatment.due_date:
                        problems.append("Plazo sin fecha exacta: se conservó el texto original.")
                else:
                    problems.append("Riesgo de referencia no encontrado")
            else:
                is_owner = row_kind == "owners"
                person, role = (str(v[2] or ""), str(v[3] or "")) if is_owner else ("", str(v[3] or ""))
                roles = (
                    [role]
                    if is_owner
                    else re.split(
                        r",|\s+y\s+(?=Oficial|Jefe|Analista|Asistente|Desarrollador|Operador|Coordinador)",
                        role,
                    )
                )
                for title in roles:
                    title = title.strip().rstrip(".")
                    d = unique_match(documents, v[1], lambda x: x.title)
                    u, pos = user_match(person), position_match(title)
                    date_value = v[4] if is_owner else v[2]
                    all_staff = normalize(title) == "todos los colaboradores"
                    DocumentLink.objects.create(
                        kind="owner" if is_owner else "access",
                        source_title=str(v[1]),
                        source_person=person,
                        source_position=title,
                        document=d,
                        user=u,
                        position=pos,
                        source_date=str(date_value or ""),
                        approved_on=valid_date(date_value),
                        all_staff=all_staff,
                        verified=False,
                        source_row=row,
                        created_by=actor,
                        updated_by=actor,
                    )
                problems.append("Revisar correspondencias y confirmar vigencia antes de activar permisos.")
            row.issue = " | ".join(problems)
            row.save()
            count += 1
            issues += bool(problems)
    workbook.close()
    if not count:
        raise ValidationError("No se encontraron filas compatibles con la estructura esperada.")
    summary["changes"] = changes
    if apply:
        batch.source.save(uploaded.name, uploaded, save=True)
    else:
        transaction.set_rollback(True)
    return {"duplicate": False, "rows": count, "issues": issues, **summary}
