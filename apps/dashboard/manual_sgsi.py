"""Lo que el Manual del SGSI (v0.7, 14/09/2026) dice de cada cláusula: los documentos que
exige y el módulo del sistema donde se trabaja. Actualizar aquí cuando cambie el manual."""

from django.urls import NoReverseMatch, reverse

MANUAL_VERSION = "Manual del SGSI v0.7"
MANUAL_META = {
    "title": "Manual del Sistema de Gestión de Seguridad de la Información",
    "version": "0.7",
    "date": "14/09/2026",
    "author": "Ana Karim Salazar",
    "approver": "Milton Guevara",
    "classification": "Uso interno",
    "status": "Borrador",
}

# (texto, nombre de ruta, argumentos)
MODULES = {
    "organigrama": ("Organigrama", "organization:chart", []),
    "mapa": ("Mapa de procesos", "processes:map", []),
    "riesgos": ("Matriz de riesgos", "traceability:risks", []),
    "anexo": ("Declaración de aplicabilidad (Anexo A)", "dashboard:annex_controls", []),
    "documentos": ("Documentos", "dashboard:entity_list", ["documentos"]),
    "responsables": ("Responsabilidades documentales", "traceability:links", []),
    "usuarios": ("Usuarios y actas", "dashboard:entity_list", ["usuarios"]),
    "auditorias": ("Auditorías", "dashboard:entity_list", ["auditorias"]),
    "reportes": ("Reportes y métricas", "dashboard:report_center", []),
    "incidentes": ("Incidentes", "dashboard:entity_list", ["incidentes"]),
    "capacitacion": ("Plan de capacitación y concienciación", "registers:detail", ["plan-capacitacion"]),
    "reuniones": ("Actas de reunión del SGSI", "registers:detail", ["actas-reunion"]),
    "medidas": ("Registro de medidas correctivas", "registers:detail", ["medidas-correctivas"]),
    "registro_incidentes": ("Registro de incidentes (RISI)", "registers:detail", ["registro-incidentes"]),
    "comunicacion": ("Comunicación con partes interesadas", "registers:detail", ["comunicacion-partes"]),
    "retencion": ("Registros y tiempos de retención", "registers:detail", ["retencion-registros"]),
}

MANUAL = {
    "4": {
        "summary": "El contexto se sustenta con el FODA, el organigrama, la lista de requisitos legales y las partes interesadas. El alcance queda definido por el documento de alcance y el mapa de procesos.",
        "modules": ["organigrama", "mapa"],
    },
    "4.1": {
        "summary": "Cuestiones externas: entorno legal, político, económico, tecnológico y competitivo, clientes y proveedores, requisitos de ciberseguridad, amenazas digitales, protección de datos personales e inteligencia artificial. Internas: estructura, políticas, cultura y desempeño del personal. También la acción climática.",
        "documents": ["Misión y Visión – FODA", "Organigrama", "Lista de requisitos legales normativos contractuales"],
        "modules": ["organigrama"],
    },
    "4.2": {
        "summary": "Las partes interesadas y sus requisitos se revisan cada año en la revisión por la dirección.",
        "documents": ["Partes interesadas", "Lista de requisitos legales normativos contractuales"],
        "modules": ["mapa"],
    },
    "4.3": {
        "summary": "Los límites del SGSI y de la certificación son los procesos del documento de alcance y del mapa de procesos.",
        "documents": ["Documento sobre el alcance del SGSI", "Mapa de procesos SIEMPRESOFT"],
        "modules": ["mapa"],
    },
    "4.4": {
        "summary": "El SGSI se establece, implementa, mantiene y mejora conforme a la NTP ISO/IEC 27001:2022.",
    },
    "5": {
        "summary": "La Gerencia General lidera el SGSI. El Oficial de Seguridad de la Información informa su desempeño a la Alta Dirección.",
        "modules": ["organigrama"],
    },
    "5.1": {
        "summary": "La Alta Dirección apoya el SGSI y se compromete a disponer los recursos necesarios.",
        "documents": ["Responsabilidad de la Alta Gerencia"],
    },
    "5.2": {
        "summary": "La Política de Seguridad de la Información es la política de alto nivel: confidencialidad, integridad y disponibilidad, gestión de riesgos, datos personales, cumplimiento legal, continuidad, mejora continua y ciberseguridad. Se complementa con la Política para el uso y gestión de la Inteligencia Artificial.",
        "documents": ["Política de Seguridad de la información", "Política para el uso y gestión de la Inteligencia Artificial"],
    },
    "5.3": {
        "summary": "Roles de la Alta Dirección y del Oficial de Seguridad; el resto de responsabilidades está en la política.",
        "documents": ["Política de Seguridad de la información", "Organigrama"],
        "modules": ["organigrama", "responsables"],
    },
    "6": {
        "summary": "Los riesgos se gestionan con la metodología de evaluación y tratamiento, y las acciones se reflejan en la Declaración de Aplicabilidad.",
        "modules": ["riesgos", "anexo"],
    },
    "6.1": {
        "summary": "Riesgos de seguridad de la información, ciberseguridad, privacidad, continuidad, servicios en la nube y proveedores críticos, según la metodología. Las acciones se reflejan en la Declaración de Aplicabilidad.",
        "documents": ["Metodología para la evaluación y tratamiento de riesgos", "Declaración de Aplicabilidad"],
        "modules": ["riesgos", "anexo"],
    },
    "6.2": {
        "summary": "Los objetivos se definen en la política y se siguen en el Plan de acción: objetivo, acción, recursos, responsable, fecha y forma de evaluación.",
        "documents": ["Política de Seguridad de la información", "Plan de acción"],
    },
    "6.3": {
        "summary": "Los cambios importantes en el SGSI se planifican y los aprueba la Alta Dirección.",
    },
    "7": {
        "summary": "Recursos según presupuesto anual, competencia y capacitación, comunicación e información documentada.",
        "modules": ["usuarios", "documentos"],
    },
    "7.1": {
        "summary": "Los recursos se evalúan en el presupuesto anual: controles de la Declaración de Aplicabilidad, obligaciones de protección de datos personales e implementación segura de inteligencia artificial, entre otros.",
        "documents": ["Presupuesto anual"],
        "modules": ["anexo"],
    },
    "7.2": {
        "summary": "Recursos Humanos gestiona selección, inducción y evaluación de desempeño. El Oficial de Seguridad capacita en seguridad, ciberseguridad, datos personales, uso responsable de la inteligencia artificial y cumplimiento.",
        "documents": ["Procedimiento de selección, capacitación, inducción del personal", "Plan de capacitación y concienciación"],
        "modules": ["capacitacion", "usuarios"],
    },
    "7.3": {
        "summary": "Todo el personal del organigrama conoce la política de seguridad y la de inteligencia artificial, sus responsabilidades sobre datos personales y los riesgos del mal uso de tecnologías digitales.",
        "modules": ["capacitacion", "organigrama"],
    },
    "7.4": {
        "summary": "La Gerencia General define qué, cuándo, quién, a quién y cómo se comunica.",
        "documents": ["Autorización de comunicación con las partes interesadas", "Decisión acerca de cómo se puede intercambiar cada tipo de datos"],
        "modules": ["comunicacion"],
    },
    "7.5": {
        "summary": "Creación, actualización, control y protección de documentos y registros, internos y externos.",
        "documents": ["Procedimiento para control de documentos y registros"],
        "modules": ["retencion", "documentos", "responsables"],
    },
    "8": {
        "summary": "Evaluación de riesgos anual o ante cambios importantes; plan de tratamiento anual con revisión trimestral.",
        "modules": ["riesgos"],
    },
    "8.1": {
        "summary": "Se planifica y controla con el plan de tratamiento de riesgos y oportunidades, el plan de acción de los objetivos y la gestión de cambios. Las herramientas de inteligencia artificial se usan según su política.",
        "documents": ["Plan de tratamiento de riesgos y oportunidades", "Plan de acción de los OSI"],
        "modules": ["riesgos"],
    },
    "8.2": {
        "summary": "Evaluación anual o ante cambios importantes, revisada por la Alta Dirección, el Oficial de Seguridad y los propietarios de cada riesgo.",
        "documents": ["Proceso de gestión de riesgos"],
        "modules": ["riesgos"],
    },
    "8.3": {
        "summary": "El plan de tratamiento se implementa cada año y su avance se revisa cada trimestre.",
        "documents": ["Proceso de gestión de riesgos (Plan de tratamiento de riesgos)", "Informe sobre evaluación y tratamiento de riesgos"],
        "modules": ["riesgos", "anexo"],
    },
    "9": {
        "summary": "Medición en el Dashboard SGSI, auditoría interna anual y revisión por la dirección al menos una vez al año.",
        "modules": ["reportes", "auditorias"],
    },
    "9.1": {
        "summary": "El Dashboard SGSI reúne el rendimiento del SGSI y de los objetivos, la matriz OEE vs OSI y la matriz EFI/EFE. Puede sumar indicadores de ciberseguridad, privacidad, continuidad y madurez de controles.",
        "documents": ["Dashboard SGSI", "Medición de indicadores"],
        "modules": ["reportes"],
    },
    "9.2": {
        "summary": "Auditoría anual según procedimiento y programa, contra los requisitos propios y la NTP ISO/IEC 27001:2022.",
        "documents": ["Procedimiento para auditoría interna"],
        "modules": ["auditorias"],
    },
    "9.3": {
        "summary": "Revisión anual con las entradas de la norma y, desde la v0.7, cambios legales, protección de datos personales, uso de inteligencia artificial y riesgos de ciberseguridad. Queda en el informe y las minutas.",
        "documents": ["Informe de revisión por parte de la Dirección", "Minutas de reunión"],
        "modules": ["reuniones", "riesgos"],
    },
    "10": {
        "summary": "La mejora continua es objetivo de la Alta Dirección; las no conformidades siguen el procedimiento de medidas correctivas.",
        "modules": ["incidentes"],
    },
    "10.1": {
        "summary": "Mejorar la idoneidad, adecuación y eficacia del SGSI.",
        "modules": ["medidas"],
    },
    "10.2": {
        "summary": "Eliminar las causas de las no conformidades es responsabilidad de todo el personal.",
        "documents": ["Procedimiento para medidas correctivas preventivas y de mejora"],
        "modules": ["medidas", "registro_incidentes", "incidentes", "reuniones"],
    },
}


def _module_links(keys):
    links = []
    for key in keys or []:
        label, name, args = MODULES[key]
        try:
            links.append({"label": label, "url": reverse(name, args=args)})
        except NoReverseMatch:
            continue
    return links


def manual_meta():
    """Datos del Manual. La versión sale del Manual cargado en el sistema; si no hay, de la guía (v0.7)."""
    meta = dict(MANUAL_META, source=MANUAL_VERSION, version_note="guía del Manual")
    try:  # 1) la versión registrada por los administradores del SGSI (con historial)
        from apps.documents.models import ManualReference

        ref = ManualReference.objects.filter(is_current=True).select_related("changed_by").first()
        if ref:
            meta.update(title=ref.title, version=ref.version, status=ref.status, author=ref.prepared_by or meta["author"],
                        approver=ref.approved_by or meta["approver"],
                        date=ref.issue_date.strftime("%d/%m/%Y") if ref.issue_date else meta["date"],
                        version_note=(f"actualizada el {ref.changed_at:%d/%m/%Y}" + (f" por {ref.changed_by.get_full_name() or ref.changed_by.username}" if ref.changed_by else "")),
                        reference_id=ref.pk)
            return meta
    except Exception:
        pass
    try:  # 2) si aún no hay registro: el Manual cargado en el sistema
        from .selectors import _best_reference_match, version_label
        from apps.documents.models import Document

        match = _best_reference_match("Manual del Sistema de Gestión de Seguridad de la Información") or _best_reference_match("Manual del SGSI")
        if match and match["kind"] == "document":
            doc = Document.objects.prefetch_related("versions").get(pk=match["id"])
            latest = next(iter(doc.versions.all()), None)
            if latest:
                meta["version"] = latest.version
                meta["status"] = latest.get_status_display() if latest.status else meta["status"]
                if latest.issue_date:
                    meta["date"] = latest.issue_date.strftime("%d/%m/%Y")
                meta["version_note"] = "versión vigente en el sistema"
        elif match:
            label = version_label(match["matched"])
            if label:
                meta["version"] = label
                meta["version_note"] = "según el archivo cargado"
    except Exception:  # la página debe abrir aunque la búsqueda falle
        pass
    return meta


def manual_for(code):
    item = MANUAL.get(str(code))
    if not item:
        return None
    return {
        "summary": item["summary"],
        "documents": item.get("documents", []),
        "modules": _module_links(item.get("modules")),
        "source": MANUAL_VERSION,
    }


# Documentos que el Manual del SGSI v0.7 exige en cada numeral, tal como aparecen en él.
# "location" solo se completa cuando el Manual la indica en sus tablas Documento / Ubicación.
REPO = "Repositorio de documentos online de Siempresoft"
MANUAL_DOCUMENTS = {
    "3.1": [
        {"name": "Política de Seguridad de la Información"},
        {"name": "Política para el uso y gestión de la Inteligencia Artificial"},
    ],
    "4.1": [
        {"name": "Misión y Visión – FODA", "location": f"{REPO}/01 - Siempresoft/Uso Interno/Documentos vigentes/01 - Misión y Visión - FODA.pdf"},
        {"name": "Organigrama", "location": f"{REPO}/07 - Área de Administración/01 - Recursos Humanos/Uso interno/Documentos vigentes/Organigrama.pdf"},
        {"name": "Lista de requisitos legales normativos contractuales", "location": f"{REPO}/01 - Siempresoft/Uso Interno/Documentos vigentes/03 – Lista de requisitos legales normativos contractuales.xlsx"},
    ],
    "4.2": [
        {"name": "Partes Interesadas", "location": f"{REPO}/01 - Siempresoft/Uso Interno/Documentos vigentes/07 - Partes Interesadas"},
        {"name": "Lista de requisitos legales normativos contractuales", "location": f"{REPO}/01 – Siempresoft/Uso Interno/Documentos vigentes/03 – Lista de requisitos legales normativos contractuales.xlsx"},
    ],
    "4.3": [
        {"name": "Documento sobre el alcance del SGSI", "location": f"{REPO}/02 - Área de Seguridad de la Información/Uso Interno/Documentos vigentes/01 – Documento sobre el alcance del SGSI.pdf"},
        {"name": "Mapa de procesos", "location": f"{REPO}/01 - Siempresoft/Uso Interno/Documentos vigentes/02 - MAPA DE PROCESOS SIEMPRESOFT.pdf"},
    ],
    "5.1": [{"name": "Responsabilidad de la Alta Gerencia"}],
    "5.2": [{"name": "Política de Seguridad de la Información"}],
    "5.3": [{"name": "Política de Seguridad de la Información"}],
    "6.1": [
        {"name": "Metodología para la evaluación y tratamiento de Riesgos"},
        {"name": "Declaración de Aplicabilidad"},
    ],
    "6.2": [{"name": "Plan de acción"}],
    "7.1": [{"name": "Presupuesto anual"}],
    "7.2": [
        {"name": "Procedimiento de selección, capacitación, inducción del personal"},
        {"name": "Perfil de puesto"},
    ],
    "7.3": [
        {"name": "Política de Seguridad de la Información"},
        {"name": "Política para el uso y gestión de la Inteligencia Artificial"},
    ],
    "7.4": [
        {"name": "Autorización de comunicación con las partes interesadas"},
        {"name": "Decisión acerca de cómo se puede intercambiar cada tipo de datos"},
    ],
    "7.5": [{"name": "Procedimiento para control de documentos y registros"}],
    "8.1": [
        {"name": "Plan de tratamiento de riesgos y oportunidades"},
        {"name": "Plan de acción de los OSI"},
    ],
    "8.2": [
        {"name": "Proceso de gestión de riesgos", "location": f"{REPO}/02 - Área de Seguridad de la Información/Gestión de riesgos/Vigentes/Proceso de gestión de riesgos_xxxx.xlsx"},
    ],
    "8.3": [
        {"name": "Proceso de gestión de riesgos (Plan de tratamiento de riesgos)", "location": f"{REPO}/02 - Área de Seguridad de la Información/Gestión de riesgos/Vigentes/Proceso de gestión de riesgos_xxxx.xlsx"},
        {"name": "Informe sobre evaluación y tratamiento de riesgos", "location": f"{REPO}/02 - Área de Seguridad de la Información/Gestión de riesgos/Vigentes/06 - Apendice_3_Informe_sobre_evaluacion_y_tratamiento.pdf"},
    ],
    "9.1": [
        {"name": "Dashboard SGSI de SIEMPRESOFT"},
        {"name": "Medición de Indicadores"},
    ],
    "9.2": [{"name": "Procedimiento para auditoría interna"}],
    "9.3": [
        {"name": "Informe de revisión por parte de la Dirección"},
        {"name": "Minutas de reunión"},
    ],
    "10.2": [{"name": "Procedimiento para medidas correctivas preventivas y de mejora"}],
}


def _requirements_map():
    """Lo que exige el Manual, editable en /admin/ (Documentos exigidos por el Manual).
    Si la tabla aún no existe o está vacía, se usa la lista del Manual v0.7."""
    try:
        from apps.documents.models import ManualDocumentRequirement

        rows = list(ManualDocumentRequirement.objects.filter(is_active=True).order_by("sort_order", "name"))
    except Exception:
        rows = []
    if not rows:
        return MANUAL_DOCUMENTS
    result = {}
    for row in rows:
        result.setdefault(row.numeral.strip().rstrip("."), []).append({"name": row.name, "location": row.location})
    return result


def manual_documents(code, include_children=False):
    """[(numeral, [documentos])] en el orden del Manual."""
    code = str(code)
    source = _requirements_map()

    def key(value):
        return [int(p) for p in value.split(".") if p.isdigit()]

    codes = sorted(
        (c for c in source if c == code or (include_children and c.startswith(code + "."))),
        key=key,
    )
    return [(c, source[c]) for c in codes]
