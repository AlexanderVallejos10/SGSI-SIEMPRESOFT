"""Activos y equipos: lista por clase y ficha con la trazabilidad completa del activo
(quién lo tiene, dónde está, qué le pasó y de qué archivo sale cada dato)."""

from collections import Counter

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404, render

from apps.core.merging import MERGED_SUFFIX

from .models import Asset, AssetClass, AssetStatus, MovementType

MOVEMENT_ICON = {
    MovementType.ASSIGNMENT: ("asignacion", "Asignado"),
    MovementType.TRANSFER: ("cambio", "Cambio de responsable"),
    MovementType.CHECKOUT: ("salida", "Salió de la oficina"),
    MovementType.CHECKIN: ("retorno", "Volvió a la oficina"),
    MovementType.RETIREMENT: ("baja", "Baja: borrado o destrucción"),
    MovementType.MAINTENANCE: ("mantenimiento", "Mantenimiento"),
    MovementType.DELIVERY: ("asignacion", "Entrega"),
    MovementType.RETURN: ("retorno", "Devolución"),
    MovementType.REPLACEMENT: ("cambio", "Reemplazo"),
}
STATUS_TONE = {
    AssetStatus.ASSIGNED: "ok", AssetStatus.AVAILABLE: "plan", AssetStatus.REVIEW: "warn",
    AssetStatus.MAINTENANCE: "warn", AssetStatus.RETIRED: "off",
}


def _responsible(asset):
    if asset.custodian_id:
        user = asset.custodian
        return {"name": user.get_full_name() or user.username, "user": user}
    if asset.custodian_name:
        return {"name": asset.custodian_name, "user": None}
    if asset.owner_role:
        return {"name": asset.owner_role, "user": None, "role": True}
    return None


@login_required
def asset_list(request):
    klass = request.GET.get("clase") or AssetClass.EQUIPMENT
    query = request.GET.get("q", "").strip()
    status = request.GET.get("estado", "")
    area = request.GET.get("area", "")

    counts = dict(Asset.objects.exclude(code__endswith=MERGED_SUFFIX).values_list("asset_class").annotate(n=Count("id")))
    tabs = [{"key": k, "label": label, "count": counts.get(k, 0)} for k, label in AssetClass.choices]

    qs = Asset.objects.exclude(code__endswith=MERGED_SUFFIX).filter(asset_class=klass).select_related("custodian").annotate(
        last_move=Max("movements__occurred_at"), last_review=Max("maintenances__performed_at"),
        reviews=Count("maintenances", distinct=True), moves=Count("movements", distinct=True),
    )
    if query:
        qs = qs.filter(
            Q(code__icontains=query) | Q(name__icontains=query) | Q(hostname__icontains=query)
            | Q(custodian_name__icontains=query) | Q(custodian__first_name__icontains=query)
            | Q(custodian__last_name__icontains=query) | Q(owner_role__icontains=query)
            | Q(area__icontains=query) | Q(process__icontains=query) | Q(asset_type__icontains=query)
        )
    if status:
        qs = qs.filter(status=status)
    if area:
        qs = qs.filter(area=area)
    rows = []
    for a in qs.order_by("code"):
        last = max([d for d in (a.last_move, a.last_review) if d], default=None)
        rows.append({"a": a, "responsible": _responsible(a), "last": last, "tone": STATUS_TONE.get(a.status, "plan")})

    in_class = Asset.objects.exclude(code__endswith=MERGED_SUFFIX).filter(asset_class=klass)
    by_status = Counter(in_class.values_list("status", flat=True))
    kpis = [
        {"label": "Activos", "value": in_class.count()},
        {"label": "Con responsable", "value": in_class.filter(Q(custodian__isnull=False) | ~Q(custodian_name="") | ~Q(owner_role="")).count()},
        {"label": "En revisión", "value": by_status.get(AssetStatus.REVIEW, 0),
         "hint": "No figuran en el último inventario" if klass == AssetClass.EQUIPMENT else ""},
        {"label": "De baja", "value": by_status.get(AssetStatus.RETIRED, 0)},
    ]
    areas = sorted({a for a in in_class.values_list("area", flat=True) if a})
    return render(request, "assets/list.html", {
        "tabs": tabs, "klass": klass, "klass_label": dict(AssetClass.choices).get(klass, ""), "rows": rows,
        "kpis": kpis, "areas": areas, "query": query, "status": status, "area": area,
        "statuses": AssetStatus.choices, "is_cid": klass in (AssetClass.INFORMATION, AssetClass.SUPPORT),
    })


@login_required
def asset_detail(request, code):
    asset = get_object_or_404(Asset.objects.select_related("custodian", "owner"), code=code)
    events = []
    for m in asset.movements.select_related("user"):
        kind, title = MOVEMENT_ICON.get(m.movement_type, ("evento", m.get_movement_type_display()))
        events.append({
            "when": m.occurred_at, "kind": kind, "title": title, "person": m.person_name or (m.user and m.user.get_full_name()),
            "user": m.user, "detail": m.reason, "extra": m.notes if m.notes != m.reason else "",
            "route": " → ".join(x for x in (m.origin, m.destination) if x), "source": m.source,
            "year_only": m.movement_type in (MovementType.ASSIGNMENT, MovementType.TRANSFER) and m.reason.startswith("Según el inventario"),
        })
    for r in asset.maintenances.all():
        events.append({
            "when": r.performed_at, "kind": "revision", "title": r.maintenance_type, "person": r.person_name,
            "detail": r.result, "route": r.technician, "source": r.source,
        })
    snapshots = list(asset.software_snapshots.all())
    for s in snapshots:
        events.append({
            "when": s.taken_at, "kind": "software", "title": "Inventario de software (Microsoft Defender)",
            "detail": f"{s.total} programas · {s.weaknesses} debilidades conocidas · {s.exploitable} con exploit público",
            "source": s.source, "date_only": True,
        })

    def sort_key(e):
        value = e["when"]
        return value.date() if hasattr(value, "date") else value
    events.sort(key=sort_key, reverse=True)

    latest_snapshot = snapshots[0] if snapshots else None
    software = sorted(latest_snapshot.items, key=lambda i: (-i["weaknesses"], i["name"].lower()))[:60] if latest_snapshot else []

    kit = []
    if asset.asset_class == AssetClass.EQUIPMENT and (asset.custodian_id or asset.custodian_name):
        same = Q(custodian=asset.custodian) if asset.custodian_id else Q(custodian_name=asset.custodian_name)
        kit = Asset.objects.exclude(code__endswith=MERGED_SUFFIX).filter(same, asset_class=AssetClass.EQUIPMENT).exclude(pk=asset.pk).order_by("code")

    risks = list(asset.affected_by_risks.all()[:30]) + list(asset.risks.all()[:30])
    counts = Counter(e["kind"] for e in events)
    return render(request, "assets/detail.html", {
        "asset": asset, "responsible": _responsible(asset), "events": events, "counts": counts,
        "software": software, "snapshot": latest_snapshot, "snapshots": snapshots, "kit": kit,
        "risks": risks, "tech_risks": (asset.extra or {}).get("riesgos_tecnologicos", []),
        "inventory": (asset.extra or {}).get("inventario", []), "note": (asset.extra or {}).get("nota", ""),
        "tone": STATUS_TONE.get(asset.status, "plan"),
    })


@login_required
def inventory_export(request):
    from django.core.exceptions import PermissionDenied

    from apps.core.exports import excel_download

    from .exporter import build_inventory

    if not request.user.has_perm("assets.view_asset"):
        raise PermissionDenied
    return excel_download(request, build_inventory(), "Inventario_de_activos_SiempreSoft", module="assets", entity="Asset")

