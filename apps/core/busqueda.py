import re

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Q, TextField
from django.db.models.functions import Cast
from django.urls import NoReverseMatch, reverse

from apps.core.merging import MERGED_SUFFIX

VARIANTES = {
    "a": "aáàäâ", "e": "eéèëê", "i": "iíìïî", "o": "oóòöô", "u": "uúùüû", "n": "nñ", "c": "cç",
}
INICIO_PALABRA = r"(^|[\s\-_/.,;:(«\"'])"
CAMPOS_EXCLUIDOS = {"password", "checksum_sha256", "source_identity_key", "import_key", "original_path", "mime_type", "color"}
TEXTO_LARGO_PERMITIDO = {"description", "notes", "event", "scenario", "threat", "summary", "requirement"}


def _clase(caracter):
    for grupo in VARIANTES.values():
        if caracter in grupo:
            return f"[{grupo}]"
    return re.escape(caracter)


def patron(palabra, desde_inicio=False):
    cuerpo = "".join(_clase(c) for c in palabra.lower())
    return f"{INICIO_PALABRA}{cuerpo}" if desde_inicio else cuerpo


def palabras(texto):
    return [p for p in re.split(r"\s+", (texto or "").strip()) if p][:6]


def campos_de_texto(model):
    campos = []
    for field in model._meta.get_fields():
        if not getattr(field, "concrete", False) or field.is_relation or field.name in CAMPOS_EXCLUIDOS or getattr(field, "choices", None):
            continue
        if isinstance(field, (models.CharField, models.SlugField, models.EmailField)) and not isinstance(field, models.FileField):
            campos.append(field.name)
        elif isinstance(field, models.TextField) and field.name in TEXTO_LARGO_PERMITIDO:
            campos.append(field.name)
    return campos


def filtro(campos, terminos, corto):
    if not campos or not terminos:
        return None
    total = Q()
    for termino in terminos:
        expresion = patron(termino, desde_inicio=corto)
        alguno = Q()
        for campo in campos:
            alguno |= Q(**{f"{campo}__iregex": expresion})
        total &= alguno
    return total


def puede(user, model, accion="view"):
    return user.is_superuser or user.has_perm(f"{model._meta.app_label}.{accion}_{model._meta.model_name}")


def url_o_none(nombre, *args, **kwargs):
    try:
        return reverse(nombre, args=args, kwargs=kwargs)
    except NoReverseMatch:
        return None


def _item(texto, detalle, url, codigo=""):
    return {"texto": str(texto)[:140], "detalle": str(detalle or "")[:140], "url": url, "codigo": str(codigo or "")[:40]}


def _codigo(obj):
    for nombre in ("business_code", "code", "username"):
        valor = getattr(obj, nombre, "")
        if valor:
            return valor
    return ""


def _buscar_modelo(model, terminos, corto, limite, qs=None, campos=None):
    campos = campos or campos_de_texto(model)
    condicion = filtro(campos, terminos, corto)
    if condicion is None:
        return []
    base = qs if qs is not None else model._default_manager.all()
    return list(base.filter(condicion)[:limite])


def fuente_paginas(user, terminos, corto, limite):
    from apps.dashboard.workbench import ENTITY_REGISTRY
    from apps.registers import schemas

    expresiones = [re.compile(patron(t, desde_inicio=corto), re.IGNORECASE) for t in terminos]
    coincide = lambda texto: all(e.search(texto) for e in expresiones)
    items = []
    for clave, cfg in ENTITY_REGISTRY.items():
        if coincide(cfg["title"]) and puede(user, cfg["model"]):
            destino = {"activos": "assets:list", "riesgos": "traceability:risks"}.get(clave)
            url = url_o_none(destino) if destino else url_o_none("dashboard:entity_list", clave)
            items.append(_item(cfg["title"], cfg.get("group", "Gestión del SGSI"), url))
    for slug, schema in {**getattr(schemas, "REGISTERS", {}), **getattr(schemas, "EXTRA_REGISTERS", {})}.items():
        nombre = schema.get("name") or schema.get("title", "").replace("{year}", "").strip()
        if nombre and coincide(nombre):
            items.append(_item(nombre.capitalize() if nombre.isupper() else nombre, "Registro del SGSI", url_o_none("registers:detail", slug)))
    for texto, detalle, nombre in (
        ("Tablero del SGSI", "Indicadores, objetivos y alineación", "dashboard_live:home"),
        ("Mapa de procesos", "Procesos del alcance del SGSI", "processes:map"),
        ("Organigrama", "Áreas y puestos", "organization:chart"),
        ("Registros del SGSI", "Registros que lleva la empresa", "registers:index"),
    ):
        if coincide(texto) or coincide(detalle):
            items.append(_item(texto, detalle, url_o_none(nombre)))
    vistos, unicos = set(), []
    for item in items:
        if item["url"] and item["url"] not in vistos:
            vistos.add(item["url"])
            unicos.append(item)
    return unicos[:limite]


def fuente_colaboradores(user, terminos, corto, limite):
    User = get_user_model()
    if not puede(user, User):
        return []
    qs = User.objects.exclude(username__endswith=MERGED_SUFFIX).order_by("-is_active", "first_name", "last_name")
    campos = [c for c in ("username", "first_name", "last_name", "business_code", "email", "area") if c in campos_de_texto(User)]
    return [
        _item(u.get_full_name() or u.username, getattr(u, "area", "") or ("Activo" if u.is_active else "Sin acceso"),
              url_o_none("dashboard:user_profile", u.pk), _codigo(u))
        for u in _buscar_modelo(User, terminos, corto, limite, qs=qs, campos=campos)
    ]


def fuente_activos(user, terminos, corto, limite):
    from apps.assets.models import Asset

    qs = Asset.objects.exclude(code__endswith=MERGED_SUFFIX).select_related("custodian").order_by("code")
    return [
        _item(a.name or a.code, " · ".join(x for x in (a.asset_type, a.custodian.get_full_name() if a.custodian else "") if x),
              url_o_none("assets:detail", a.code), a.code)
        for a in _buscar_modelo(Asset, terminos, corto, limite, qs=qs)
    ]


def fuente_procesos(user, terminos, corto, limite):
    from apps.processes.models import ProcessNode

    return [
        _item(p.name, getattr(p.category, "name", "") if hasattr(p, "category") else "", url_o_none("processes:process_detail", p.pk), p.code)
        for p in _buscar_modelo(ProcessNode, terminos, corto, limite, qs=ProcessNode.objects.select_related("category").order_by("code"))
    ]


def fuente_riesgos(user, terminos, corto, limite):
    from apps.risks.models import Risk

    if not puede(user, Risk):
        return []
    return [
        _item(getattr(r, "event", "") or getattr(r, "name", "") or r.code, getattr(r, "category", ""), url_o_none("traceability:risk_edit", r.pk), r.code)
        for r in _buscar_modelo(Risk, terminos, corto, limite, qs=Risk.objects.order_by("code"))
    ]


def fuente_documentos(user, terminos, corto, limite):
    from apps.documents.models import Document
    from apps.traceability.access import can_read_document

    candidatos = _buscar_modelo(Document, terminos, corto, limite * 3, qs=Document.objects.order_by("code"))
    visibles = [d for d in candidatos if can_read_document(user, d)][:limite]
    return [_item(d.title or d.code, getattr(d, "document_type", "") or "Documento", url_o_none("dashboard:document_detail", d.pk), d.code) for d in visibles]


def fuente_archivos(user, terminos, corto, limite):
    from apps.documents.models import SourceArtifact
    from apps.traceability.access import require_artifact

    campos = [c for c in ("original_name", "code", "extension") if c in campos_de_texto(SourceArtifact)]
    qs = SourceArtifact.objects.order_by("original_name")
    if hasattr(SourceArtifact, "duplicate_of"):
        qs = qs.filter(duplicate_of__isnull=True)
    resultado = []
    for artefacto in _buscar_modelo(SourceArtifact, terminos, corto, limite * 3, qs=qs, campos=campos):
        try:
            require_artifact(user, artefacto)
        except PermissionDenied:
            continue
        extension = (artefacto.extension or "").lower().lstrip(".")
        nombre = "dashboard:artifact_table" if extension in {"xlsx", "xlsm"} else "dashboard:artifact_view"
        resultado.append(_item(artefacto.original_name, extension.upper() or "Archivo", url_o_none(nombre, artefacto.pk), artefacto.code))
        if len(resultado) >= limite:
            break
    return resultado


def fuente_organizacion(user, terminos, corto, limite):
    from apps.organization.models import OrganizationalArea, Position

    items = [
        _item(a.name, "Área", url_o_none("organization:area_detail", a.pk), _codigo(a))
        for a in _buscar_modelo(OrganizationalArea, terminos, corto, limite)
    ]
    for p in _buscar_modelo(Position, terminos, corto, limite, qs=Position.objects.select_related("area")):
        items.append(_item(p.title, getattr(p.area, "name", "") or "Puesto", url_o_none("organization:chart") + f"#puesto-{p.pk}", _codigo(p)))
    return items[:limite]


def fuente_filas_registro(user, terminos, corto, limite):
    from apps.registers import schemas
    from apps.registers.models import RegisterEntry

    qs = RegisterEntry.objects.annotate(texto=Cast("data", TextField())).order_by("-year", "register", "order")
    resultado = []
    for fila in _buscar_modelo(RegisterEntry, terminos, corto, limite, qs=qs, campos=["texto"]):
        schema = schemas.get(fila.register) or {}
        nombre = schema.get("name") or schema.get("title", fila.register).replace("{year}", str(fila.year or "")).strip()
        valores = [str(v) for v in (fila.data or {}).values() if v not in (None, "", [], {})]
        resumen = next((v for v in valores if any(re.search(patron(t), v, re.IGNORECASE) for t in terminos)), valores[0] if valores else "")
        url = url_o_none("registers:detail", fila.register)
        resultado.append(_item(resumen, f"{nombre}{' · ' + str(fila.year) if fila.year else ''}", f"{url}?q={terminos[0]}" if url else None))
    return resultado


def fuente_tablero(user, terminos, corto, limite):
    from apps.dashboard_live.models import DashboardMetric, OesiMetric, SecurityObjective, StrategicFactor, StrategicObjective

    inicio = url_o_none("dashboard_live:home") or "/"
    numero = next((int(t[1:]) for t in terminos if re.fullmatch(r"[mM]\d{1,3}", t)), None)
    resultado = []
    for model, seccion, prefijo, detalle in (
        (DashboardMetric, "indicadores", "M", "Indicador del SGSI"),
        (OesiMetric, "objetivos", "OESI", "Objetivo específico de seguridad"),
        (SecurityObjective, "alineacion", "", "Objetivo de seguridad"),
        (StrategicObjective, "alineacion", "", "Objetivo estratégico"),
        (StrategicFactor, "estrategia", "", "Factor estratégico"),
    ):
        qs = model.objects.filter(dataset__is_current=True)
        if numero is not None and prefijo == "M":
            encontrados = list(qs.filter(metric_id=numero)[:limite])
        else:
            encontrados = _buscar_modelo(model, terminos, corto, limite, qs=qs)
        for obj in encontrados:
            codigo = getattr(obj, "code", "") or (f"{prefijo}{obj.metric_id}" if hasattr(obj, "metric_id") else "")
            resultado.append(_item(obj.description, detalle, f"{inicio}#{seccion}", codigo))
    return resultado[:limite]


def fuente_generica(clave):
    def buscar(user, terminos, corto, limite):
        from apps.dashboard.workbench import ENTITY_REGISTRY

        model = ENTITY_REGISTRY[clave]["model"]
        if not puede(user, model):
            return []
        return [
            _item(str(obj), ENTITY_REGISTRY[clave]["title"], url_o_none("dashboard:entity_detail", clave, obj.pk), _codigo(obj))
            for obj in _buscar_modelo(model, terminos, corto, limite)
        ]
    return buscar


ESPECIALES = {"usuarios", "activos", "riesgos", "documentos"}


def fuentes():
    from apps.dashboard.workbench import ENTITY_REGISTRY

    lista = [
        ("paginas", "Ir a", "i-home", fuente_paginas),
        ("colaboradores", "Colaboradores", "i-users", fuente_colaboradores),
        ("activos", "Activos y equipos", "i-assets", fuente_activos),
        ("procesos", "Procesos", "i-process", fuente_procesos),
        ("riesgos", "Riesgos", "i-risk", fuente_riesgos),
        ("tablero", "Tablero del SGSI", "i-reports", fuente_tablero),
        ("documentos", "Documentos", "i-docs", fuente_documentos),
        ("archivos", "Archivos Excel y PDF", "i-file-check", fuente_archivos),
        ("organizacion", "Áreas y puestos", "i-org", fuente_organizacion),
    ]
    for clave, cfg in ENTITY_REGISTRY.items():
        if clave not in ESPECIALES:
            lista.append((clave, cfg["title"], cfg.get("icon", "i-docs"), fuente_generica(clave)))
    lista.append(("filas", "Filas de registros", "i-book", fuente_filas_registro))
    return lista


def buscar(user, texto, limite=4, solo=None):
    terminos = palabras(texto)
    if not terminos:
        return []
    corto = len(texto.strip()) < 3
    grupos = []
    for clave, titulo, icono, funcion in fuentes():
        if solo and clave != solo:
            continue
        try:
            items = [i for i in funcion(user, terminos, corto, limite) if i.get("url")]
        except Exception:
            items = []
        if items:
            grupos.append({"clave": clave, "titulo": titulo, "icono": icono, "items": items})
    return grupos
