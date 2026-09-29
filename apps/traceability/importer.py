"""Explicit workbook ingestion. Exact matches only; preserve unresolved source rows."""

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
from apps.processes.models import ProcessNode
from apps.risks.models import Risk, RiskAssessment, RiskTreatment

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
    for sheet in workbook:
        if sheet.title not in expected[kind]:
            continue
        if sheet.max_row > 10000 or sheet.max_column > 100:
            raise ValidationError("La hoja excede el tamaño admitido.")
        for index, values in enumerate(sheet.iter_rows(values_only=True), 1):
            v = list(values) + [None] * 20
            row_kind = kind
            if kind == "risks":
                if index < 5:
                    continue
                if sheet.title == "Matriz de riesgos":
                    if not re.fullmatch(r"R[0-9]+", str(v[0] or "")):
                        continue
                elif not re.fullmatch(r"R[0-9]+", str(v[1] or "")):
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
                risk = Risk.objects.filter(code=str(v[0])).first()
                if risk:
                    problems.append(
                        "Código existente: no se sobrescribió el riesgo; comparar con esta fuente."
                    )
                else:
                    risk = Risk.objects.create(
                        code=v[0],
                        process=str(v[1] or ""),
                        origin=str(v[2] or ""),
                        category=str(v[3] or ""),
                        threat=str(v[4] or ""),
                        event=str(v[5] or ""),
                        motivation=str(v[6] or ""),
                        scenario=str(v[7] or v[5] or "Pendiente"),
                        existing_controls=str(v[11] or ""),
                        owner_position=position_match(v[12]),
                        owner=user_match(v[12]),
                        created_by=actor,
                        updated_by=actor,
                    )
                    process = unique_match(processes, v[1], lambda p: p.name)
                    if process:
                        process.risks.add(risk)
                    else:
                        problems.append("Proceso por vincular: " + str(v[1] or "sin dato"))
                    probability, impact = number(v[9], 4), number(v[8], 5)
                    if probability and impact:
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
                    else:
                        problems.append("Evaluación incompleta")
                    if not risk.owner_id and not risk.owner_position_id:
                        problems.append("Propietario por vincular: " + str(v[12] or "sin dato"))
                    if str(v[0]) == "R51":
                        problems.append(
                            "Verificar etiquetas originales de consecuencia y probabilidad; se conservó la fuente."
                        )
                row.risk = risk
            elif kind == "risks":
                risk = Risk.objects.filter(code=v[1]).first()
                row.risk = risk
                if risk:
                    # Repeated files never create duplicate treatment actions.
                    treatment, created = RiskTreatment.objects.get_or_create(
                        risk=risk,
                        action=str(v[5] or "Pendiente"),
                        defaults={
                            "option": str(v[4] or ""),
                            "responsible": user_match(v[6]),
                            "start_date": valid_date(v[7]),
                            "due_date": valid_date(v[8]),
                            "source_start": str(v[7] or ""),
                            "source_end": str(v[8] or ""),
                            "resources": str(v[9] or ""),
                            "status": str(v[10] or "pending"),
                            "residual_impact": number(v[11], 5),
                            "residual_probability": number(v[12], 4),
                            "closed_date": valid_date(v[14]),
                            "notes": str(v[15] or ""),
                            "created_by": actor,
                            "updated_by": actor,
                        },
                    )
                    if not created:
                        problems.append("Tratamiento existente: no se sobrescribió.")
                    if not treatment.responsible_id:
                        problems.append("Responsable por vincular: " + str(v[6] or ""))
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
    if apply:
        batch.source.save(uploaded.name, uploaded, save=True)
    else:
        transaction.set_rollback(True)
    return {"duplicate": False, "rows": count, "issues": issues}
