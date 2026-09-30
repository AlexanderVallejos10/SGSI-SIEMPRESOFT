"""Carga en el sistema los activos reales de SiempreSoft y su historial, desde el paquete
apps/assets/data/siempresoft_activos.json (armado con scripts/build_seed_siempresoft.py).

- Colaboradores: se crean como usuarios SIN acceso (inactivos, estado «no confirmado») para poder
  enlazarles sus equipos. Un administrador los activa cuando corresponda.
- Equipos (SS1-XXX-NNN): responsable, ambiente e historial por año según el inventario de escritorios y PCs.
- Salidas y retornos (registro 02), revisiones periódicas, inventario de software (Defender),
  bajas (actas de borrado), BYOD y activos de información, soporte y tecnológicos (matriz de riesgos 2026).

Se puede ejecutar varias veces: cada dato tiene una clave de importación y se actualiza, no se duplica.
"""

import datetime as dt
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.assets.models import (
    Asset,
    AssetClass,
    AssetMovement,
    AssetSoftwareSnapshot,
    AssetStatus,
    Maintenance,
    MovementType,
)

DEFAULT_FILE = Path(__file__).resolve().parents[2] / "data" / "siempresoft_activos.json"
TYPES = {
    "CPU": "Computadora (CPU)", "LAP": "Laptop", "MON": "Monitor", "TEC": "Teclado", "MOU": "Mouse",
    "EST": "Estabilizador", "SUP": "Supresor de picos", "ANT": "Antena WiFi", "CAM": "Cámara web",
    "AUR": "Auriculares", "CAR": "Cargador", "ESC": "Escritorio", "MOV": "Celular", "TAB": "Tablet",
}
LEVEL_ORDER = {"bajo": 1, "medio": 2, "alto": 3, "muy alto": 4, "critico": 4}


def when(value, hour=9):
    """Fecha ISO → fecha y hora con zona horaria (las fuentes solo traen el día)."""
    if not value:
        return None
    try:
        day = dt.date.fromisoformat(value[:10])
    except ValueError:
        return None
    return timezone.make_aware(dt.datetime.combine(day, dt.time(hour, 0)))


def name_key(value):
    import unicodedata

    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(c for c in value if not unicodedata.combining(c)).lower()
    tokens = [t for t in re.split(r"[^a-z]+", value) if t and t not in ("ing", "de", "del", "la")]
    return tokens


def existing_by_name(User, name):
    """Usuario ya registrado con el mismo nombre y apellido (sin tildes). Solo si hay uno."""
    tokens = name_key(name)
    if len(tokens) < 2:
        return None
    candidates = User.objects.filter(last_name__icontains=tokens[-1]) | User.objects.filter(last_name__icontains=tokens[1])
    matches = []
    for user in candidates.distinct():
        mine = name_key(f"{user.first_name} {user.last_name}")
        if len(mine) >= 2 and mine[0] == tokens[0] and set(tokens[1:]) & set(mine[1:]):
            matches.append(user)
    return matches[0] if len(matches) == 1 else None


class Command(BaseCommand):
    help = "Carga activos, colaboradores e historial reales de SiempreSoft."

    def add_arguments(self, parser):
        parser.add_argument("--archivo", default=str(DEFAULT_FILE), help="Paquete JSON de datos.")
        parser.add_argument("--sin-usuarios", action="store_true",
                            help="No crear usuarios; los responsables quedan solo con su nombre.")

    # ------------------------------------------------------------------ personas
    def load_people(self, people, create_users):
        User = get_user_model()
        by_key, names = {}, {}
        created = 0
        for p in people:
            names[p["key"]] = p["name"]
            if not create_users:
                continue
            email = p.get("email", "")
            user = User.objects.filter(email__iexact=email).first() if email else None
            base = (email.split("@")[0] if email else slugify(p["name"]).replace("-", "."))[:140] or "colaborador"
            if user is None:
                user = existing_by_name(User, p["name"])  # el colaborador ya registrado manda: se usa su usuario y su código
            if user is None:
                user = User.objects.filter(username=base).first()
            if user is None:
                code, n = f"COL-{base.upper()}"[:30], 1
                while User.objects.filter(business_code=code).exists():
                    n += 1
                    code = f"COL-{base.upper()}"[:27] + f"-{n}"
                first, _, last = p["name"].partition(" ")
                user = User(
                    username=base, email=email, first_name=first[:150], last_name=last[:150],
                    business_code=code, is_active=False,
                )
                user.set_unusable_password()
                created += 1
            # Solo se completan datos vacíos: nunca se pisa lo que un administrador ya corrigió.
            for field, value in (("area", p.get("area", "")), ("position", p.get("position", ""))):
                if value and not getattr(user, field, ""):
                    setattr(user, field, value[:120])
            if p.get("start") and not user.employment_start:
                user.employment_start = dt.date.fromisoformat(p["start"][:10])
            if p.get("end") and not user.employment_end:
                user.employment_end = dt.date.fromisoformat(p["end"][:10])
            if not user.source_document:
                user.source_document = "; ".join(p.get("sources", []))[:255]
                user.source_reference = "Carga de datos SiempreSoft (repositorio OneDrive)"
                user.source_verified = False
                user.status = "inactive" if p.get("end") else "unknown"
            user.save()
            by_key[p["key"]] = user
        return by_key, names, created

    # ------------------------------------------------------------------ ayudas
    def same_code(self, code):
        """Si ya existe un activo con un código equivalente (SS1-CPU-012 = SS1-CPU-12), se usa ese:
        un activo, un código, sin duplicados al volver a cargar."""
        from apps.accounts.unify import asset_key

        if not hasattr(self, "_codes"):
            self._codes = {asset_key(c): c for c in Asset.objects.values_list("code", flat=True)}
        key = asset_key(code)
        existing = self._codes.get(key)
        if existing:
            return existing
        self._codes[key] = code
        return code

    def movement(self, key, **fields):
        obj, _ = AssetMovement.objects.update_or_create(import_key=key[:120], defaults=fields)
        return obj

    def handle(self, *args, **opts):
        path = Path(opts["archivo"])
        if not path.exists():
            raise CommandError(f"No existe el paquete de datos: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        stats = defaultdict(int)
        with transaction.atomic():
            users, names, stats["usuarios nuevos (sin acceso)"] = self.load_people(data["people"], not opts["sin_usuarios"])
            person = lambda key: users.get(key)
            label = lambda key, fallback="": names.get(key, "") or fallback

            # ---------------------------------------------------------- equipos del inventario
            last_year = max((e["year"] for a in data["equipment"] for e in a["history"]), default=None)
            assets = {}
            kit_by_person_year = defaultdict(list)
            for eq in data["equipment"]:
                hist = eq["history"]
                latest = hist[-1] if hist else {}
                key = latest.get("user", "")
                in_last = bool(latest) and latest["year"] == last_year
                status = (AssetStatus.ASSIGNED if (key or latest.get("user_text")) else AssetStatus.AVAILABLE) if in_last else AssetStatus.REVIEW
                name = eq["type"] + (f" · {eq['hostname']}" if eq.get("hostname") else "")
                asset, _ = Asset.objects.update_or_create(code=self.same_code(eq["code"]), defaults={
                    "asset_type": eq["type"], "name": name[:180], "asset_class": AssetClass.EQUIPMENT,
                    "hostname": eq.get("hostname", "")[:120], "model": eq.get("board", "")[:100],
                    "custodian": person(key) if in_last else None,
                    "custodian_name": (label(key, latest.get("user_text", "")) if in_last else "")[:160],
                    "area": latest.get("area", "")[:160],
                    "location": " · ".join(x for x in (latest.get("level", ""), latest.get("area", "")) if x)[:160],
                    "status": status, "source": eq.get("source", "")[:255],
                    "extra": {"inventario": hist, "ultimo_inventario": latest.get("year"),
                              "nota": "" if in_last else f"No figura en el inventario {last_year}; última vez en {latest.get('year')}."},
                })
                assets[eq["code"]] = asset
                stats["equipos"] += 1
                previous = None
                for entry in hist:
                    who = entry.get("user") or entry.get("user_text") or ""
                    if eq["prefix"] in ("CPU", "LAP") and entry.get("user"):
                        kit_by_person_year[(entry["user"], entry["year"])].append(asset)
                    if who == previous:
                        continue
                    self.movement(
                        f"inv:{eq['code']}:{entry['year']}",
                        asset=asset,
                        movement_type=MovementType.ASSIGNMENT if previous is None else MovementType.TRANSFER,
                        user=person(entry.get("user", "")),
                        person_name=(label(entry.get("user", ""), entry.get("user_text", "")) or "Sin responsable")[:160],
                        origin=(label(previous, previous or "") if previous else "")[:160],
                        destination=" · ".join(x for x in (entry.get("level", ""), entry.get("area", "")) if x)[:160],
                        occurred_at=when(f"{entry['year']}-01-01"),
                        reason=f"Según el inventario de escritorios y PCs {entry['year']}.",
                        source=eq.get("source", "")[:255],
                    )
                    stats["asignaciones y cambios de responsable"] += 1
                    previous = who

            def asset_for(code, prefix, source):
                if code in assets:
                    return assets[code]
                asset, _ = Asset.objects.get_or_create(code=self.same_code(code), defaults={
                    "asset_type": TYPES.get(prefix, "Equipo"), "name": f"{TYPES.get(prefix, 'Equipo')} {code}",
                    "asset_class": AssetClass.EQUIPMENT, "status": AssetStatus.REVIEW, "source": source[:255],
                    "extra": {"nota": "Solo aparece en el registro de salidas; no figura en el inventario anual."},
                })
                assets[code] = asset
                stats["equipos que solo aparecen en salidas"] += 1
                return asset

            # ---------------------------------------------------------- salidas y retornos
            for c in data["checkouts"]:
                if not c.get("out"):
                    continue
                asset = asset_for(c["code"], c["code"].split("-")[1], c["source"])
                base = f"{c['code']}:{c['out']}:{slugify(c['person'])[:30]}"
                reason = " · ".join(x for x in (
                    f"Autorizado por {c['authorized_by']}" if c.get("authorized_by") else "",
                    f"Plazo de retorno: {c['term']}" if c.get("term") else "",
                    f"Medio: {c['medium']}" if c.get("medium") else "",
                ) if x)
                self.movement(f"out:{base}", asset=asset, movement_type=MovementType.CHECKOUT,
                              user=person(c.get("email", "")), person_name=label(c.get("email", ""), c["person"])[:160],
                              origin="Oficina", destination="Fuera de las instalaciones", occurred_at=when(c["out"]),
                              reason=reason, notes=c.get("label", ""), source=c["source"][:255])
                stats["salidas"] += 1
                if c.get("back"):
                    self.movement(f"in:{base}", asset=asset, movement_type=MovementType.CHECKIN,
                                  user=person(c.get("email", "")), person_name=label(c.get("email", ""), c["person"])[:160],
                                  origin="Fuera de las instalaciones", destination="Oficina", occurred_at=when(c["back"], 18),
                                  reason="Retorno registrado en el registro 02.", source=c["source"][:255])
                    stats["retornos"] += 1

            # ---------------------------------------------------------- equipos de cada persona por año
            def devices(key, year):
                for y in (year, year - 1, year + 1, year - 2):
                    found = kit_by_person_year.get((key, y))
                    if found:
                        return list(dict.fromkeys(found))
                return []

            # ---------------------------------------------------------- revisiones periódicas
            for r in data["reviews"]:
                year = int(r["date"][:4])
                targets = devices(r.get("email", ""), year)
                if not targets:
                    stats["revisiones sin equipo identificado"] += 1
                    continue
                for asset in targets:
                    Maintenance.objects.update_or_create(
                        import_key=f"rev:{r['date']}:{asset.code}:{slugify(r['person'])[:30]}"[:120],
                        defaults={
                            "asset": asset, "maintenance_type": "Revisión periódica de seguridad",
                            "performed_at": when(r["date"]), "technician": "Área de Seguridad de la Información",
                            "result": r.get("evidence", "") or "Revisado sin observaciones.",
                            "person_name": label(r.get("email", ""), r["person"])[:160], "source": r["source"][:255],
                        },
                    )
                    stats["revisiones registradas en equipos"] += 1

            # ---------------------------------------------------------- inventario de software (Defender)
            for s in data["software"]:
                targets = devices(s.get("email", ""), int(s["date"][:4]))
                if not targets:
                    stats["inventarios de software sin equipo"] += 1
                    continue
                items = s["items"]
                for asset in targets[:1]:  # el equipo principal (CPU o laptop) de esa persona ese año
                    AssetSoftwareSnapshot.objects.update_or_create(
                        import_key=f"sw:{s['machine']}:{s['date']}:{asset.code}"[:120],
                        defaults={
                            "asset": asset, "taken_at": dt.date.fromisoformat(s["date"]), "items": items,
                            "total": len(items), "weaknesses": sum(i["weaknesses"] for i in items),
                            "exploitable": sum(1 for i in items if i["exploit"]), "source": s["source"][:255],
                        },
                    )
                    stats["inventarios de software"] += 1

            # ---------------------------------------------------------- activos de información, soporte y tecnológicos
            for rows, klass in ((data["information_assets"], AssetClass.INFORMATION), (data["support_assets"], AssetClass.SUPPORT)):
                for a in rows:
                    Asset.objects.update_or_create(code=self.same_code(a["code"]), defaults={
                        "asset_type": a["category"][:80], "name": a["name"][:180], "asset_class": klass,
                        "process": a["process"][:160], "owner_role": a["owner"][:160],
                        "confidentiality": a["c"][:40], "integrity": a["i"][:40], "availability": a["a"][:40],
                        "valuation": a["value"][:20], "status": AssetStatus.ASSIGNED if a["owner"] else AssetStatus.AVAILABLE,
                        "source": a["source"][:255],
                    })
                    stats[f"activos {klass.label.lower()}"] += 1
            for a in data["technology_assets"]:
                levels = [r["level"] for r in a["risks"] if r.get("level")]
                top = max(levels, key=lambda v: LEVEL_ORDER.get(slugify(v).replace("-", " "), 0), default="")
                Asset.objects.update_or_create(code=self.same_code(a["code"]), defaults={
                    "asset_type": a["category"][:80], "name": a["name"][:180], "asset_class": AssetClass.TECHNOLOGY,
                    "process": a["process"][:160], "owner_role": a["owner"][:160], "criticality": top[:30],
                    "status": AssetStatus.ASSIGNED if a["owner"] else AssetStatus.AVAILABLE,
                    "source": a["source"][:255], "extra": {"riesgos_tecnologicos": a["risks"]},
                })
                stats["activos tecnológicos"] += 1

            # ---------------------------------------------------------- bajas (actas de borrado y destrucción)
            host_index = {a.hostname.lower(): a for a in assets.values() if a.hostname}
            for n, d in enumerate(sorted(data["disposals"], key=lambda x: (x["date"], x["source"])), start=1):
                text = d["support"]
                code = re.search(r"SS1-[A-Z]{3}-\d{3}", text)
                asset = assets.get(code.group(0)) if code else next(
                    (a for h, a in host_index.items() if h and h in text.lower()), None)
                if asset is None:
                    year = d["date"][:4] or "s-f"
                    code = f"BAJA-{year}-{hashlib.md5(d['source'].encode()).hexdigest()[:6].upper()}"
                    asset, _ = Asset.objects.update_or_create(code=self.same_code(code), defaults={
                        "asset_type": "Soporte dado de baja", "name": text[:180], "asset_class": AssetClass.DISPOSED,
                        "status": AssetStatus.RETIRED, "source": d["source"][:255],
                        "extra": {"anio": year},
                    })
                else:
                    asset.status = AssetStatus.RETIRED
                    asset.save(update_fields=["status"])
                self.movement(f"baja:{d['source']}", asset=asset, movement_type=MovementType.RETIREMENT,
                              person_name=d.get("by", "")[:160], origin="", destination="Borrado o destrucción",
                              occurred_at=when(d["date"]) or when("2019-01-01"),
                              reason=d.get("method", ""), notes="Acta de borrado y destrucción de registros.",
                              source=d["source"][:255])
                stats["bajas"] += 1

            # ---------------------------------------------------------- BYOD
            per_person = defaultdict(int)
            for b in data["byod"]:
                per_person[b["person"]] += 1
                code = f"BYOD-{slugify(b['person'])[:30]}-{per_person[b['person']]}".upper()
                retired = b.get("status", "").lower() in ("baja", "inactivo", "retirado")
                asset, _ = Asset.objects.update_or_create(code=self.same_code(code), defaults={
                    "asset_type": b.get("device") or "Dispositivo personal", "asset_class": AssetClass.BYOD,
                    "name": f"{b.get('device') or 'Dispositivo'} de {b['person']}"[:180],
                    "custodian": users.get(b.get("email", "")), "custodian_name": label(b.get("email", ""), b["person"])[:160],
                    "area": b.get("area", "")[:160], "status": AssetStatus.RETIRED if retired else AssetStatus.ASSIGNED,
                    "source": b["source"][:255], "extra": {"descripcion": b.get("description", ""), "observacion": b.get("note", "")},
                })
                if b.get("date"):
                    self.movement(f"byod:{code}", asset=asset, movement_type=MovementType.ASSIGNMENT,
                                  user=users.get(b.get("email", "")), person_name=label(b.get("email", ""), b["person"])[:160],
                                  destination="Autorizado como BYOD", occurred_at=when(b["date"]),
                                  reason=b.get("description", ""), source=b["source"][:255])
                stats["dispositivos BYOD"] += 1

        self.stdout.write(self.style.SUCCESS("Carga de activos de SiempreSoft terminada:"))
        for key, value in stats.items():
            self.stdout.write(f"  {key}: {value}")
