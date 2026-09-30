"""Carga y enlaza TODO lo real de SiempreSoft que llegó del repositorio de OneDrive:

  1. Registros del SGSI y activos con su historial (cargar_datos_siempresoft).
  2. Unifica colaboradores: si una persona ya existía en el sistema, se usa su usuario y su código.
  3. Organigrama: ubica a cada colaborador vigente en su puesto según su cargo más reciente.
  4. Documentos que pide el Manual, con su archivo real y su versión (dejan de decir «falta»).
  5. Páginas 4.1 y 4.2 (Misión y Visión, Organigrama, Requisitos legales, Partes interesadas).
  6. Matriz de riesgos (Karim 2026 y modelo), responsabilidades documentales y autorizaciones.
  7. Incidentes (registro RISI), auditorías con sus hallazgos y acciones, y vulnerabilidades (Defender).

Cada paso va en su propia transacción: si uno falla se deshace solo ese paso y los demás siguen.
Se puede ejecutar las veces que haga falta: nada se duplica.
"""

import datetime as dt
import hashlib
import json
import re
import shutil
import unicodedata
from collections import defaultdict
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.text import slugify

APP_DIR = Path(__file__).resolve().parents[2]
DOCS_DIR = APP_DIR / "data" / "documentos"
TRACE_DIR = APP_DIR.parent / "traceability" / "data"
ASSETS_FILE = APP_DIR.parent / "assets" / "data" / "siempresoft_activos.json"
SOURCE_REF = "Carga de datos SiempreSoft (repositorio OneDrive)"
STOP = {"de", "del", "la", "el", "y", "los", "las", "ing", "al", "a"}


def singular(word):
    """Desarrolladores → desarrollador, Consultores → consultor, Analistas → analista."""
    if word.endswith("ores") and len(word) > 6:
        return word[:-2]
    if word.endswith("s") and len(word) > 4 and not word.endswith("ss"):
        return word[:-1]
    return word


def tokens(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if not unicodedata.combining(c)).lower()
    return [singular(t) for t in re.split(r"[^a-z0-9+]+", value) if t and t not in STOP]


def aware(value, hour=9):
    value = str(value or "")[:10]
    try:
        day = dt.date.fromisoformat(value)
    except ValueError:
        return None
    return timezone.make_aware(dt.datetime.combine(day, dt.time(hour, 0)))


def control_for(text):
    from apps.controls.models import Control

    codes = re.findall(r"(?:A\.?\s*)?\b([5-8]\.\d{1,2})\b", str(text or ""))
    for code in codes:
        control = Control.objects.filter(code__in=[code, f"A.{code}", f"A {code}", f"A.{code}."]).first()
        if control:
            return control
    return None


class Command(BaseCommand):
    help = "Carga y enlaza todos los datos reales de SiempreSoft (registros, activos, organigrama, documentos, riesgos, incidentes, auditorías y vulnerabilidades)."

    def add_arguments(self, parser):
        parser.add_argument("--paso", action="append", default=[],
                            help="Ejecuta solo ese paso (se puede repetir): datos, unificar, organigrama, documentos, contexto, dashboard, riesgos, incidentes, auditorias, vulnerabilidades.")

    # ------------------------------------------------------------------ ayudas
    def people_data(self):
        if not ASSETS_FILE.exists():
            return []
        return json.loads(ASSETS_FILE.read_text(encoding="utf-8")).get("people", [])

    def user_by_name(self, name, exclude_imported=False):
        User = get_user_model()
        wanted = tokens(name)
        if len(wanted) < 2:
            return None
        qs = User.objects.all()
        if exclude_imported:
            qs = qs.exclude(business_code__startswith="COL-")
        found = []
        for user in qs.filter(last_name__isnull=False):
            mine = tokens(f"{user.first_name} {user.last_name}")
            if len(mine) >= 2 and mine[0] == wanted[0] and set(mine[1:]) & set(wanted[1:]):
                found.append(user)
        return found[0] if len(found) == 1 else None

    def user_for(self, text):
        """Persona del registro → usuario: por nombre («Elio Mondragón») o por cargo («Jefe de Producción»)."""
        from apps.organization.models import PositionAssignment

        text = str(text or "").strip()
        if not text:
            return None
        user = self.user_by_name(re.split(r"\s[-–(]\s?", text)[0])
        if user:
            return user
        position = self.position_for(text)
        if position:
            current = PositionAssignment.objects.filter(position=position, end_date__isnull=True).select_related("user").first()
            if current:
                return current.user
        return None

    def position_for(self, role):
        from apps.organization.models import Position

        wanted = tokens(re.sub(r"(?i)\s*-\s*practicante.*$", "", role or ""))
        if not wanted:
            return None
        positions = list(Position.objects.filter(is_active=True))
        exact = [p for p in positions if tokens(p.title) == wanted]
        if len(exact) == 1:
            return exact[0]
        inside = [p for p in positions if tokens(p.title) and (set(tokens(p.title)) <= set(wanted) or set(wanted) <= set(tokens(p.title)))]
        return inside[0] if len(inside) == 1 else None

    def officer(self):
        """Oficial de Seguridad de la Información: quien lleva los registros del SGSI."""
        User = get_user_model()
        return (User.objects.filter(email__iexact="ksalazar@siempresoft.com").first()
                or self.user_for("Oficial de Seguridad de la Información")
                or User.objects.filter(is_superuser=True).order_by("date_joined").first())

    # ------------------------------------------------------------------ 1. registros y activos
    def step_datos(self):
        call_command("cargar_datos_siempresoft", stdout=self.stdout)
        return {}

    # ------------------------------------------------------------------ 2. unificar colaboradores
    def step_unificar(self):
        """Un código, una persona: se unifican las cuentas duplicadas (misma persona con dos registros)
        y los activos con códigos equivalentes. Los casos dudosos se informan y no se tocan."""
        from apps.accounts.unify import duplicate_assets, duplicate_groups, merge, merge_assets

        merged, doubtful = 0, []
        for keep, dups, is_doubtful in duplicate_groups():
            if is_doubtful:
                doubtful.append(keep.get_full_name() or keep.username)
                continue
            merge(keep, dups)
            merged += len(dups)
        assets = 0
        for keep, dups in duplicate_assets():
            merge_assets(keep, dups)
            assets += len(dups)
        out = {"personas duplicadas unificadas": merged, "activos duplicados unificados": assets}
        if doubtful:
            out["para revisar a mano (unificar_personas)"] = ", ".join(doubtful)
        return out

    # ------------------------------------------------------------------ 3. organigrama
    def step_organigrama(self, actor):
        from apps.organization.models import PositionAssignment
        from apps.organization.services import assign_user_to_position

        User = get_user_model()
        people = self.people_data()
        stats = defaultdict(int)
        pending = []
        current_2026 = set()
        if ASSETS_FILE.exists():
            data = json.loads(ASSETS_FILE.read_text(encoding="utf-8"))
            for eq in data.get("equipment", []):
                for h in eq.get("history", []):
                    if h.get("year") == 2026 and h.get("user"):
                        current_2026.add(h["user"])
        ordered = sorted(people, key=lambda p: (p.get("cargo_actual") or {}).get("fecha", ""), reverse=True)
        for p in ordered:
            role = p.get("cargo_actual") or {}
            if not role or p.get("end"):
                stats["sin cargo o retirados (no se ubican)"] += 1
                continue
            recent = role.get("fecha", "") >= "2025" or p.get("key") in current_2026
            if not recent:
                stats["último cargo anterior a 2025 (no se ubican)"] += 1
                continue
            user = (User.objects.filter(email__iexact=p["email"]).first() if p.get("email") else None) or self.user_by_name(p["name"])
            if user is None:
                stats["sin usuario"] += 1
                continue
            if PositionAssignment.objects.filter(user=user, end_date__isnull=True).exists():
                stats["ya tenían puesto (se respeta)"] += 1
                continue
            position = self.position_for(role["cargo"])
            if position is None:
                pending.append(f"{p['name']} – {role['cargo']}")
                continue
            taken = PositionAssignment.objects.filter(position=position, end_date__isnull=True).count()
            if position.max_occupants and taken >= position.max_occupants:
                pending.append(f"{p['name']} – {role['cargo']} (el puesto «{position.title}» ya está ocupado)")
                continue
            start = dt.date.fromisoformat(role["fecha"][:10]) if role.get("fecha") else timezone.localdate()
            assign_user_to_position(assignment=PositionAssignment(
                position=position, user=user, start_date=start, is_primary=True,
                notes=f"Ubicado por la carga de datos de SiempreSoft: {role['cargo']} según {role.get('fuente', '')} ({role.get('fecha', '')}).",
            ), actor=actor)
            try:
                from apps.organization.services import sync_user_organization
                sync_user_organization(user.pk)
            except Exception:
                pass
            stats["ubicados en su puesto"] += 1
        for line in pending:
            self.stdout.write(f"    pendiente de ubicar: {line}")
        stats["pendientes de ubicar (cargo sin puesto igual en el organigrama)"] = len(pending)
        return stats

    # ------------------------------------------------------------------ 4. documentos del Manual
    def step_documentos(self, actor):
        from apps.dashboard.document_workspace import upload_version
        from apps.dashboard.manual_documents import _new_code
        from apps.documents.models import Document, SGSISection

        manifest = json.loads((DOCS_DIR / "manifiesto.json").read_text(encoding="utf-8"))
        stats = defaultdict(int)
        for entry in manifest["documentos"]:
            path = DOCS_DIR / entry["archivo"]
            if not path.exists():
                stats["archivo no encontrado"] += 1
                continue
            document = Document.objects.filter(title__iexact=entry["titulo"]).first()
            if document is None:
                document = Document.objects.create(code=_new_code(entry["numerales"][0]), title=entry["titulo"],
                                                   category="Manual del SGSI", created_by=actor, updated_by=actor)
                stats["documentos nuevos"] += 1
            for numeral in entry["numerales"]:
                section = SGSISection.objects.filter(code=numeral).first()
                if section:
                    document.sgsi_sections.add(section)
            content = path.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            if document.versions.filter(checksum_sha256=digest).exists() or document.versions.filter(version=entry["version"]).exists():
                stats["ya tenían ese archivo o esa versión"] += 1
                continue
            upload_version(document, actor, SimpleUploadedFile(entry["archivo"], content), entry["version"],
                           f"Carga inicial desde el repositorio de SiempreSoft: {entry['origen']}", entry["estado"])
            stats["versiones cargadas"] += 1
        for missing in manifest.get("faltan", []):
            self.stdout.write(f"    no enviado: {', '.join(missing['numerales'])} {missing['documento']} — {missing['motivo']}")
        stats["documentos que no llegaron"] = len(manifest.get("faltan", []))
        return stats

    # ------------------------------------------------------------------ tablero (Excel Dashboard SGSI 2026)
    def step_dashboard(self, actor):
        from django.core.cache import cache

        from apps.dashboard_live.importer import import_workbook
        from apps.dashboard_live.overview import CACHE_KEY

        path = DOCS_DIR / "Dashboard SGSI de SIEMPRESOFT_2026.xlsx"
        if not path.exists():
            return {"tablero": "archivo no incluido"}
        dataset = import_workbook(path=path, version_label="2026", actor=actor, original_name=path.name, apply_changes=True)
        # Corrige cargas anteriores que etiquetaron el Excel de 2021 («_3») como 2026.
        from apps.dashboard_live.models import DashboardDataset
        relabeled = (DashboardDataset.objects.exclude(pk=dataset.pk).filter(version_label="2026")
                     .exclude(original_name__icontains="2026").update(version_label="anterior (formato 2021)"))
        cache.delete(CACHE_KEY)
        return {"tablero vigente": f"{dataset.original_name}: {dataset.sgsi_metrics.count()} indicadores, "
                                   f"{dataset.oesi_metrics.count()} OESI, {dataset.security_objectives.count()} OSI",
                "versiones anteriores reetiquetadas": relabeled}

    # ------------------------------------------------------------------ 5. páginas 4.1 y 4.2
    def step_contexto(self, actor):
        manifest = json.loads((DOCS_DIR / "manifiesto.json").read_text(encoding="utf-8"))
        imports = Path(settings.BASE_DIR) / "imports"
        imports.mkdir(exist_ok=True)
        copied = 0
        for entry in manifest["contexto"]:
            target = imports / entry["archivo"]
            if not target.exists():  # si ya hay un archivo con ese nombre, se respeta
                shutil.copyfile(DOCS_DIR / entry["archivo"], target)
                copied += 1
        call_command("seed_context41", apply=True, stdout=self.stdout)
        call_command("seed_context42", apply=True, stdout=self.stdout)
        return {"archivos de 4.1 y 4.2 preparados": copied}

    # ------------------------------------------------------------------ 6. riesgos, responsabilidades y autorizaciones
    def step_riesgos(self, actor):
        from apps.traceability.importer import import_workbook

        stats = {}
        for name, kind, label in (
            ("Matriz_Identificacion_Valoracion_Riesgos_SiempreSoft_2026.xlsx", "risks", "matriz de riesgos 2026"),
            ("Matriz_Identificacion_Riesgos_modelo.xlsx", "risks", "matriz de riesgos modelo"),
            ("01_-_Lista_asignación_de_propietarios_de_documentos.xlsx", "owners", "responsabilidades documentales"),
            ("10_-_Lista_de_personas_autorizadas_para_acceder_a_documentos_clasificados_como_RESTRINGIDA_Y_CONFIDENCIAL.xlsx", "access", "autorizaciones de acceso"),
        ):
            path = TRACE_DIR / name
            if not path.exists():
                stats[label] = "archivo no incluido"
                continue
            try:
                with transaction.atomic():  # cada archivo por separado: un error no arrastra a los demás
                    result = import_workbook(SimpleUploadedFile(name, path.read_bytes()), kind, actor, apply=True)
            except Exception as exc:
                stats[label] = f"no se pudo importar: {exc}"
                continue
            stats[label] = "ya estaba importada" if result.get("duplicate") else f"{result['rows']} filas ({result['issues']} con observaciones)"
        return stats

    # ------------------------------------------------------------------ 7a. incidentes
    def step_incidentes(self, actor):
        from apps.incidents.models import Incident
        from apps.registers.models import RegisterEntry

        reporter = self.officer()
        if reporter is None:
            return {"omitido": "no hay un usuario para registrar los incidentes"}
        severity = {"alto": "high", "medio": "medium", "bajo": "low", "critico": "critical", "crítico": "critical"}
        stats = defaultdict(int)
        for n, row in enumerate(RegisterEntry.objects.filter(register="registro-incidentes").order_by("year", "order"), start=1):
            d = row.data
            raw = re.sub(r"(?i)\.xlsx$", "", d.get("nro", "")).replace("_", "-").strip().upper()
            code = raw or f"RISI-{row.year}-{n:02d}"
            if row.year and str(row.year) not in code:
                code = f"{code}-{row.year}"
            closed = bool(d.get("cierre")) or d.get("estado", "").lower() in ("implementado", "atendido", "cerrado")
            detail = [d.get("descripcion", "")]
            for label, key in (("Acción tomada", "accion"), ("Tiempo de atención", "tiempo"), ("Formulario", "formulario"),
                               ("Fecha de cierre", "cierre"), ("Estado en el registro", "estado")):
                if d.get(key):
                    detail.append(f"{label}: {d[key]}")
            if not d.get("criterio"):
                detail.append("Criterio de severidad no indicado en el registro (se toma Medio).")
            incident, created = Incident.objects.update_or_create(code=code[:50], defaults={
                "incident_type": "Incidente de seguridad de la información",
                "severity": severity.get(d.get("criterio", "").strip().lower(), "medium"),
                "occurred_at": aware(d.get("fecha")) or aware(f"{row.year or 2019}-01-01"),
                "reporter": reporter, "responsible": self.user_for(d.get("responsable")),
                "description": "\n".join(detail), "status": "closed" if closed else "reported",
            })
            control = control_for(d.get("control"))
            if control:
                incident.controls.add(control)
            stats["incidentes nuevos" if created else "incidentes actualizados"] += 1
        return stats

    # ------------------------------------------------------------------ 7b. auditorías
    def step_auditorias(self, actor):
        from apps.assurance.models import Audit, Finding, ImprovementAction
        from apps.registers.models import RegisterEntry

        lead = self.officer()
        if lead is None:
            return {"omitido": "no hay un usuario para registrar las auditorías"}
        groups = defaultdict(list)
        for row in RegisterEntry.objects.filter(register="medidas-correctivas").order_by("year", "order"):
            d = row.data
            if not d.get("tipo", "").lower().startswith("auditor"):
                continue
            groups[(d["tipo"].strip(), d.get("fecha") or f"{row.year}-01-01")].append((row.year, d))
        stats = defaultdict(int)
        for (kind, date), rows in sorted(groups.items(), key=lambda kv: kv[0][1]):
            done = all(r.get("estado", "").lower().startswith("implementad") for _, r in rows)
            code = f"AUD-{date}-{slugify(kind)[:24]}".upper()[:50]
            audit, created = Audit.objects.update_or_create(code=code, defaults={
                "audit_type": kind[:80], "scope": "Alcance del SGSI de SiempreSoft (documento sobre el alcance del SGSI).",
                "criteria": "ISO/IEC 27001:2022 y documentación del SGSI de SiempreSoft.",
                "start_date": dt.date.fromisoformat(date[:10]), "end_date": dt.date.fromisoformat(date[:10]),
                "lead_auditor": lead, "status": "closed" if done else "open",
            })
            stats["auditorías nuevas" if created else "auditorías actualizadas"] += 1
            # Un mismo hallazgo puede estar repetido en el registro (p. ej. 2025, n.º 25, 33, 39 y 40) con estados
            # que se contradicen. Se carga una vez; si los estados no coinciden, queda abierto con una nota.
            merged = {}
            for i, (year, d) in enumerate(rows, start=1):
                key = f"{code}-{d.get('nro') or i}"[:50]
                merged.setdefault(key, []).append(d)
            for fcode, dups in merged.items():
                d = dups[0]
                states = [x.get("estado", "").strip() for x in dups]
                conflict = len({s.lower() for s in states}) > 1
                implemented = not conflict and states[0].lower().startswith("implementad")
                text = d.get("descripcion", "")
                ftype = ("No conformidad" if re.search(r"(?i)\bNC\b|no conformidad", text)
                         else "Observación" if re.search(r"(?i)^obs", text)
                         else "Oportunidad de mejora" if re.search(r"(?i)oportunidad|^OM\b", text) else "Hallazgo")
                responsible = self.user_for(d.get("responsable")) or lead
                note = (f"\n\nEn el registro de medidas figura {len(dups)} veces con estados distintos: {', '.join(states)}. "
                        "Queda abierto hasta confirmar cuál es el correcto." if conflict else "")
                finding, _ = Finding.objects.update_or_create(code=fcode, defaults={
                    "audit": audit, "finding_type": ftype,
                    "description": text + (f"\n\n{d['detalle']}" if d.get("detalle") else "") + note,
                    "responsible": responsible, "status": "closed" if implemented else "open",
                    "control": control_for(f"{d.get('detalle', '')} {text}"),
                    "criterion": f"Responsable según el registro: {d.get('responsable', '')}"[:1000],
                })
                action = finding.actions.first()
                values = {
                    "description": f"Medida registrada en «{d.get('formulario') or 'el registro centralizado de medidas correctivas'}».",
                    "responsible": responsible, "due_date": dt.date.fromisoformat(date[:10]),
                    "status": "implemented" if implemented else ("por confirmar" if conflict else (states[0] or "pending").lower()[:40]),
                    "effectiveness_notes": f"Días de atraso según el registro: {d.get('atraso') or '0'}.",
                }
                if action:
                    for key, value in values.items():
                        setattr(action, key, value)
                    action.save()
                else:
                    ImprovementAction.objects.create(finding=finding, **values)
                stats["hallazgos con su acción"] += 1
                if conflict:
                    stats["hallazgos repetidos en el registro con estados distintos (quedan abiertos)"] += 1
        return stats

    # ------------------------------------------------------------------ 7c. vulnerabilidades
    def step_vulnerabilidades(self, actor):
        from apps.assets.models import Asset
        from apps.incidents.models import Vulnerability

        fallback = self.officer()
        stats = defaultdict(int)
        for asset in Asset.objects.filter(software_snapshots__isnull=False).distinct():
            snap = asset.software_snapshots.order_by("-taken_at").first()
            responsible = asset.custodian or fallback
            if responsible is None:
                continue
            for item in snap.items:
                if not item.get("weaknesses"):
                    continue
                code = f"VUL-{asset.code}-{slugify(item['name'])[:24]}".upper()[:50]
                exploit = bool(item.get("exploit"))
                _, created = Vulnerability.objects.update_or_create(code=code, defaults={
                    "source": f"Microsoft Defender – inventario de software del {snap.taken_at:%d/%m/%Y}"[:160],
                    "asset": asset, "severity": "high" if exploit or item["weaknesses"] >= 10 else "medium",
                    "detected_at": aware(snap.taken_at.isoformat()), "responsible": responsible, "status": "review",
                    "solution": (f"Actualizar {item['name']} ({item.get('vendor', '')}) desde la versión {item.get('version', '')}: "
                                 f"{item['weaknesses']} debilidades conocidas{', con exploit público' if exploit else ''}. "
                                 "Verificar en la última revisión periódica si ya se actualizó."),
                })
                stats["vulnerabilidades nuevas" if created else "vulnerabilidades actualizadas"] += 1
        return stats

    # ------------------------------------------------------------------ ejecución
    def handle(self, *args, **opts):
        User = get_user_model()
        actor = User.objects.filter(is_superuser=True, is_active=True).order_by("date_joined").first()
        steps = [
            ("datos", "Registros del SGSI y activos", self.step_datos),
            ("unificar", "Colaboradores ya registrados (sin duplicar)", self.step_unificar),
            ("organigrama", "Organigrama", lambda: self.step_organigrama(actor)),
            ("documentos", "Documentos que pide el Manual", lambda: self.step_documentos(actor)),
            ("contexto", "Páginas 4.1 y 4.2", lambda: self.step_contexto(actor)),
            ("dashboard", "Tablero del SGSI (Excel 2026)", lambda: self.step_dashboard(actor)),
            ("riesgos", "Riesgos, responsabilidades y autorizaciones", lambda: self.step_riesgos(actor)),
            ("incidentes", "Incidentes", lambda: self.step_incidentes(actor)),
            ("auditorias", "Auditorías, hallazgos y acciones", lambda: self.step_auditorias(actor)),
            ("vulnerabilidades", "Vulnerabilidades", lambda: self.step_vulnerabilidades(actor)),
        ]
        wanted = set(opts["paso"])
        failures = []
        for key, title, run in steps:
            if wanted and key not in wanted:
                continue
            self.stdout.write(self.style.MIGRATE_HEADING(f"▸ {title}"))
            try:
                with transaction.atomic():
                    result = run() or {}
            except Exception as exc:  # el paso se deshace completo; los demás siguen
                failures.append((title, exc))
                self.stdout.write(self.style.ERROR(f"  No se completó (se deshizo este paso): {exc}"))
                continue
            for label, value in result.items():
                self.stdout.write(f"  {label}: {value}")
        from django.core.cache import cache

        from apps.dashboard_live.overview import CACHE_KEY

        cache.delete(CACHE_KEY)  # el tablero se recalcula con lo recién cargado
        if failures:
            self.stdout.write(self.style.WARNING(f"Terminó con {len(failures)} paso(s) sin completar; el resto quedó cargado."))
        else:
            self.stdout.write(self.style.SUCCESS("Todo cargado y enlazado."))
