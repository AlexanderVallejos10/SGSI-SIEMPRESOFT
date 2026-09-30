"""Estado del SGSI tomado de los módulos del sistema (riesgos, incidentes, medidas, auditorías,
activos, documentos del Manual, controles y vulnerabilidades) para el tablero de inicio.

Cada sección se calcula por separado: si una falla (módulo sin datos o sin migrar) el tablero
muestra las demás. El resultado se guarda en caché unos minutos."""

import logging
from collections import Counter, defaultdict

from django.core.cache import cache


log = logging.getLogger(__name__)
CACHE_KEY = "sgsi-dashboard-overview-v4"
LEVEL_TONE = {"Muy alto": "crit", "Alto": "bad", "Medio": "warn", "Bajo": "ok", "Muy bajo": "low"}


def _safe(fn):
    try:
        return fn()
    except Exception as exc:  # una sección con problemas no debe tumbar el inicio
        log.warning("Tablero: no se pudo calcular %s: %s", fn.__name__, exc)
        return None


def risks():
    from apps.risks.models import Risk
    from apps.traceability.services import LEVELS, risk_level

    heat = [[0] * 5 for _ in range(4)]
    levels = Counter()
    total = 0
    for risk in Risk.objects.filter(is_active=True).prefetch_related("assessments"):
        total += 1
        latest = max(risk.assessments.all(), key=lambda a: a.assessed_at, default=None)
        if latest is None or not (1 <= latest.probability <= 4 and 1 <= latest.impact <= 5):
            levels["Pendiente"] += 1
            continue
        heat[latest.probability - 1][latest.impact - 1] += 1
        levels[risk_level(latest.probability, latest.impact)] += 1
    grid = []
    for p in range(4, 0, -1):  # probabilidad alta arriba
        grid.append({"p": p, "cells": [
            {"i": i, "count": heat[p - 1][i - 1], "level": LEVELS[p - 1][i - 1], "tone": LEVEL_TONE[LEVELS[p - 1][i - 1]]}
            for i in range(1, 6)
        ]})
    order = ["Muy alto", "Alto", "Medio", "Bajo", "Muy bajo", "Pendiente"]
    return {
        "total": total, "grid": grid,
        "levels": [{"name": k, "count": levels.get(k, 0), "tone": LEVEL_TONE.get(k, "muted")} for k in order if levels.get(k)],
        "high": levels.get("Muy alto", 0) + levels.get("Alto", 0),
    }


def incidents():
    from apps.incidents.models import Incident

    by_year = defaultdict(Counter)
    open_count = 0
    for occurred_at, severity, status in Incident.objects.values_list("occurred_at", "severity", "status"):
        by_year[occurred_at.year][severity] += 1
        open_count += status not in ("closed", "cerrado")
    years = sorted(by_year)
    series = [
        {"name": "Crítico", "tone": "crit", "values": [by_year[y]["critical"] for y in years]},
        {"name": "Alto", "tone": "bad", "values": [by_year[y]["high"] for y in years]},
        {"name": "Medio", "tone": "warn", "values": [by_year[y]["medium"] for y in years]},
        {"name": "Bajo", "tone": "ok", "values": [by_year[y]["low"] for y in years]},
    ]
    series = [s for s in series if any(s["values"])]
    return {"total": sum(sum(c.values()) for c in by_year.values()), "open": open_count, "years": years, "series": series,
            "last_year": years[-1] if years else None, "last_count": sum(by_year[years[-1]].values()) if years else 0}


def corrective():
    from apps.registers.models import RegisterEntry

    by_year = defaultdict(Counter)
    for year, data in RegisterEntry.objects.filter(register="medidas-correctivas").values_list("year", "data"):
        state = str(data.get("estado", "")).strip().lower()
        by_year[year or 0]["done" if state.startswith("implementad") else "pending"] += 1
    years = sorted(y for y in by_year if y)
    series = [
        {"name": "Implementadas", "tone": "ok", "values": [by_year[y]["done"] for y in years]},
        {"name": "Pendientes", "tone": "warn", "values": [by_year[y]["pending"] for y in years]},
    ]
    done = sum(c["done"] for c in by_year.values())
    total = sum(sum(c.values()) for c in by_year.values())
    return {"total": total, "done": done, "pending": total - done, "pct": round(100 * done / total) if total else 0,
            "years": years, "series": series}


def audits():
    from apps.assurance.models import Audit, Finding

    findings = Counter(Finding.objects.values_list("finding_type", flat=True))
    closed = Finding.objects.filter(status="closed").count()
    total = sum(findings.values())
    tones = {"No conformidad": "bad", "Observación": "warn", "Oportunidad de mejora": "info", "Hallazgo": "calm"}
    parts = [{"label": k, "value": v, "tone": tones.get(k, "calm")} for k, v in findings.most_common()]
    last = Audit.objects.order_by("-start_date").first()
    return {"audits": Audit.objects.count(), "findings": total, "closed": closed, "open": total - closed, "parts": parts,
            "last": {"type": last.audit_type, "date": last.start_date.isoformat()} if last else None}


def assets():
    from apps.assets.models import Asset, AssetClass, AssetStatus

    counts = Counter(Asset.objects.values_list("asset_class", flat=True))
    labels = dict(AssetClass.choices)
    tones = {"equipment": "info", "information": "calm", "support": "violet", "technology": "ok", "byod": "warn", "disposed": "muted"}
    parts = [{"label": labels.get(k, k), "value": v, "tone": tones.get(k, "calm")} for k, v in counts.most_common()]
    equipment = Asset.objects.filter(asset_class=AssetClass.EQUIPMENT)
    return {"total": sum(counts.values()), "parts": parts,
            "assigned": equipment.filter(status=AssetStatus.ASSIGNED).count(),
            "review": equipment.filter(status=AssetStatus.REVIEW).count()}


def documents():
    from apps.dashboard.manual_documents import manual_requirements

    rows = []
    for clause in ("4", "5", "6", "7", "8", "9", "10"):
        items = [d for block in manual_requirements(clause, include_children=True) for d in block["documents"]]
        found = sum(1 for d in items if d.get("found"))
        if items:
            rows.append({"clause": clause, "found": found, "total": len(items), "pct": round(100 * found / len(items))})
    found = sum(r["found"] for r in rows)
    total = sum(r["total"] for r in rows)
    return {"rows": rows, "found": found, "total": total, "pct": round(100 * found / total) if total else 0}


def controls():
    from apps.controls.models import Control

    applicability = Counter(Control.objects.values_list("applicability", flat=True))
    implementation = Counter(Control.objects.values_list("implementation_status", flat=True))
    total = sum(applicability.values())
    tones = {"applicable": "ok", "not_applicable": "muted", "pending": "warn"}
    labels = {"applicable": "Aplicables", "not_applicable": "No aplicables", "pending": "Por definir"}
    parts = [{"label": labels.get(k, k), "value": v, "tone": tones.get(k, "calm")} for k, v in applicability.most_common()]
    return {"total": total, "parts": parts,
            "implemented": implementation.get("implemented", 0)}


def vulnerabilities():
    from apps.incidents.models import Vulnerability

    sev = Counter(Vulnerability.objects.values_list("severity", flat=True))
    order = [("critical", "Crítica", "crit"), ("high", "Alta", "bad"), ("medium", "Media", "warn"), ("low", "Baja", "ok")]
    rows = [{"label": label, "count": sev.get(k, 0), "tone": tone} for k, label, tone in order if sev.get(k)]
    peak = max((r["count"] for r in rows), default=1)
    for r in rows:
        r["pct"] = round(100 * r["count"] / peak)
    return {"total": sum(sev.values()), "rows": rows}


def registers_total():
    from apps.registers.models import RegisterEntry

    return RegisterEntry.objects.count()


def system_overview(refresh=False):
    data = None if refresh else cache.get(CACHE_KEY)
    if data is None:
        data = {name: _safe(fn) for name, fn in (
            ("risks", risks), ("incidents", incidents), ("corrective", corrective), ("audits", audits),
            ("assets", assets), ("documents", documents), ("controls", controls),
            ("vulnerabilities", vulnerabilities), ("registers", registers_total),
        )}
        cache.set(CACHE_KEY, data, 300)
    return data
