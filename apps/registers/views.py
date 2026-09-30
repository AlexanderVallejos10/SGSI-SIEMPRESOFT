import json
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Max
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import exporters, importers
from .models import RegisterEntry, RegisterImport
from .schemas import GROUPS, MONTHS, REGISTERS, clean_value, get, section as get_section, summary


def _can_edit(user):
    return user.is_superuser or user.has_perm("registers.change_registerentry")


def _can_import(user):
    return user.is_superuser or user.has_perm("registers.import_registerentry")


def _schema_or_404(slug):
    schema = get(slug)
    if schema is None:
        raise Http404("Registro no encontrado.")
    return schema


def _years(slug):
    return sorted(
        {y for y in RegisterEntry.objects.filter(register=slug).values_list("year", flat=True) if y},
        reverse=True,
    )


def _entries(slug, year):
    qs = RegisterEntry.objects.filter(register=slug)
    return list(qs.filter(year=year) if year else qs)


def _row_html(request, slug, schema, entry):
    return render_to_string(
        f"registers/_row_{schema['layout']}.html",
        {"e": entry, "schema": schema, "slug": slug, "months": MONTHS, "can_edit": _can_edit(request.user),
         "section": get_section(schema, entry.section), "current_month": timezone.localdate().month},
        request=request,
    )


@login_required
def index(request):
    stats = {
        row["register"]: row
        for row in RegisterEntry.objects.values("register").annotate(n=Count("id"), last=Max("updated_at"))
    }
    cards = []
    for slug, schema in REGISTERS.items():
        s = stats.get(slug, {})
        cards.append({
            "slug": slug, "schema": schema, "rows": s.get("n", 0), "last": s.get("last"),
            "years": _years(slug) if schema["by_year"] else [],
        })
    groups = [
        {"name": name, "cards": [c for c in cards if c["schema"].get("group") == name]}
        for name in GROUPS
    ]
    groups = [g for g in groups if g["cards"]]
    return render(request, "registers/index.html", {"cards": cards, "groups": groups, "total": len(cards)})


@login_required
def detail(request, slug):
    schema = _schema_or_404(slug)
    years = _years(slug) if schema["by_year"] else []
    year = None
    if schema["by_year"]:
        requested = request.GET.get("anio", "")
        year = int(requested) if requested.isdigit() else (years[0] if years else timezone.localdate().year)
        if year not in years:
            years = sorted(set(years) | {year}, reverse=True)
    entries = _entries(slug, year)
    sections = []
    for sec in schema["sections"]:
        rows = [e for e in entries if e.section == sec["key"]]
        groups = []
        if sec.get("group_by"):
            for e in rows:
                key = e.data.get(sec["group_by"], "") or "Sin asignar"
                if not groups or groups[-1]["name"] != key:
                    groups.append({"name": key, "rows": []})
                groups[-1]["rows"].append(e)
        elif rows:
            groups = [{"name": "", "rows": rows}]
        sections.append({"meta": sec, "groups": groups, "count": len(rows)})
    context = {
        "slug": slug,
        "schema": schema,
        "year": year,
        "years": years,
        "sections": sections,
        "summary": summary(slug, entries),
        "months": MONTHS,
        "current_month": timezone.localdate().month,
        "now_year": timezone.localdate().year,
        "can_edit": _can_edit(request.user),
        "can_import": _can_import(request.user),
        "last_import": RegisterImport.objects.filter(register=slug, year=year).first(),
    }
    return render(request, "registers/detail.html", context)


@login_required
@require_POST
def create_row(request, slug):
    schema = _schema_or_404(slug)
    if not _can_edit(request.user):
        raise PermissionDenied
    payload = json.loads(request.body or "{}")
    sec = get_section(schema, payload.get("section", ""))
    year = payload.get("year") if schema["by_year"] else None
    data = {f["key"]: clean_value(f, payload.get("data", {}).get(f["key"], f.get("default", ""))) for f in sec["fields"]}
    last = RegisterEntry.objects.filter(register=slug, year=year, section=sec["key"]).order_by("-order").first()
    entry = RegisterEntry.objects.create(
        register=slug, year=year, section=sec["key"], data=data,
        order=(last.order + 1) if last else 1, created_by=request.user, updated_by=request.user,
    )
    return JsonResponse({"html": _row_html(request, slug, schema, entry), "summary": summary(slug, _entries(slug, year))})


@login_required
@require_POST
def update_row(request, pk):
    entry = get_object_or_404(RegisterEntry, pk=pk)
    schema = _schema_or_404(entry.register)
    if not _can_edit(request.user):
        raise PermissionDenied
    payload = json.loads(request.body or "{}")
    fields = {f["key"]: f for f in get_section(schema, entry.section)["fields"]}
    data = dict(entry.data)
    for key, value in payload.items():
        if key in fields:
            data[key] = clean_value(fields[key], value)
    entry.data = data
    entry.updated_by = request.user
    entry.save(update_fields=["data", "updated_by", "updated_at"])
    return JsonResponse({
        "html": _row_html(request, entry.register, schema, entry),
        "summary": summary(entry.register, _entries(entry.register, entry.year)),
    })


@login_required
@require_POST
def delete_row(request, pk):
    entry = get_object_or_404(RegisterEntry, pk=pk)
    if not _can_edit(request.user):
        raise PermissionDenied
    slug, year = entry.register, entry.year
    entry.delete()
    return JsonResponse({"ok": True, "summary": summary(slug, _entries(slug, year))})


@login_required
@require_POST
def import_excel(request, slug):
    schema = _schema_or_404(slug)
    if not _can_import(request.user):
        raise PermissionDenied
    accept = tuple(schema.get("accept", [".xlsx", ".xlsm"]))
    upload = request.FILES.get("file")
    detail_url = reverse("registers:detail", args=[slug])
    if upload is None or not upload.name.lower().endswith(accept + (".xlsx", ".xlsm")):
        messages.error(request, f"Suba un archivo {', '.join(accept)}.")
        return redirect(detail_url)
    default_year = None
    if schema["by_year"]:
        raw = request.POST.get("year", "")
        default_year = int(raw) if raw.isdigit() else importers.year_from_name(upload.name) or timezone.localdate().year
    try:
        rows = importers.read(slug, upload, upload.name)
    except Exception:  # archivo dañado o con otro formato
        rows = []
    if not rows:
        messages.error(request, f"No se reconocieron filas en «{upload.name}». Revise que sea el formato de «{schema['name']}» o descargue la plantilla.")
        return redirect(detail_url + (f"?anio={default_year}" if default_year else ""))

    # Un mismo archivo puede traer varios años (p. ej. todas las actas de 2019 a 2026).
    buckets = {}
    for sec, data in rows:
        data = dict(data)
        row_year = data.pop("_year", None)
        year = (row_year or default_year) if schema["by_year"] else None
        buckets.setdefault(year, []).append((sec, data))

    replace = request.POST.get("mode", "replace") == "replace"
    with transaction.atomic():
        for year, items in buckets.items():
            if replace:
                RegisterEntry.objects.filter(register=slug, year=year).delete()
                start = 0
            else:
                start = RegisterEntry.objects.filter(register=slug, year=year).count()
            RegisterEntry.objects.bulk_create([
                RegisterEntry(register=slug, year=year, section=sec, data=data, order=start + i + 1,
                              created_by=request.user, updated_by=request.user)
                for i, (sec, data) in enumerate(items)
            ])
            RegisterImport.objects.create(
                register=slug, year=year, file_name=os.path.basename(upload.name), rows=len(items),
                replaced=replace, created_by=request.user,
            )
    years = sorted(y for y in buckets if y)
    detail = ", ".join(f"{y}: {len(buckets[y])}" for y in years) if len(years) > 1 else ""
    messages.success(
        request,
        f"Se importaron {len(rows)} filas desde «{upload.name}»"
        + (f" ({detail})." if detail else (f" para {years[0]}." if years else "."))
        + (" Reemplazaron a las anteriores de ese año." if replace else " Se agregaron a las existentes."),
    )
    shown = years[-1] if years else None
    return redirect(detail_url + (f"?anio={shown}" if shown else ""))


@login_required
def export_excel(request, slug):
    schema = _schema_or_404(slug)
    year = request.GET.get("anio")
    year = int(year) if year and year.isdigit() else None
    blank = request.GET.get("plantilla") == "1"
    entries = [] if blank else _entries(slug, year if schema["by_year"] else None)
    by_section = {}
    for e in entries:
        by_section.setdefault(e.section, []).append(e)
    content = exporters.build(slug, schema, by_section, year)
    name = schema["name"] + (f" {year}" if year else "") + (" - plantilla" if blank else "")
    response = HttpResponse(content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{name}.xlsx"'
    return response
