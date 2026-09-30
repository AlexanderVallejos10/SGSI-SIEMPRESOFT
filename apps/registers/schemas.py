"""Cada registro del SGSI que antes vivía en Excel: sus campos, secciones e indicadores.

Los alias son los encabezados tal como aparecen en los Excel de SiempreSoft; el importador
los usa para reconocer las columnas aunque cambien de posición."""

MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Set", "Oct", "Nov", "Dic"]
MONTH_LETTERS = ["E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]

REGISTERS = {
    "plan-capacitacion": {
        "name": "Plan de capacitación y concienciación",
        "clause": "7.2 y 7.3",
        "annex": "6.3",
        "description": "Qué conocimientos se refuerzan en cada perfil de puesto, en qué meses y con qué modalidad, "
                       "y los temas de concienciación para todo el personal.",
        "source": "05 - Plan de capacitación y concienciación <año>.xlsx",
        "title": "PLAN DE CAPACITACIÓN Y CONCIENCIACIÓN {year}",
        "by_year": True,
        "layout": "timeline",
        "sections": [
            {
                "key": "capacitacion",
                "label": "Capacitación",
                "sheet": "Capacitación",
                "group_by": "perfil",
                "fields": [
                    {"key": "perfil", "label": "Perfil de puesto", "type": "text", "aliases": ["perfil de puesto"]},
                    {"key": "tema", "label": "Conocimientos y habilidades", "type": "longtext",
                     "aliases": ["conocimientos y habilidades"], "required": True},
                    {"key": "meses", "label": "Meses", "type": "months"},
                    {"key": "modalidad", "label": "Modalidad", "type": "choice", "aliases": ["modalidad"],
                     "choices": ["Capacitación externa", "Capacitación interna", "Autoaprendizaje", "Charla"]},
                    {"key": "estado", "label": "Estado", "type": "choice", "default": "Programada",
                     "choices": ["Programada", "Realizada", "Reprogramada", "Cancelada"]},
                ],
            },
            {
                "key": "concienciacion",
                "label": "Concienciación",
                "sheet": "Concienciación",
                "fields": [
                    {"key": "tema", "label": "Tema", "type": "longtext", "aliases": ["tema"], "required": True},
                    {"key": "meses", "label": "Meses", "type": "months"},
                    {"key": "modalidad", "label": "Modalidad", "type": "choice", "aliases": ["modalidad"],
                     "choices": ["Virtual", "Presencial", "Correo electrónico", "Charla"]},
                    {"key": "estado", "label": "Estado", "type": "choice", "default": "Programada",
                     "choices": ["Programada", "Realizada", "Reprogramada", "Cancelada"]},
                ],
            },
        ],
    },
    "software-autorizado": {
        "name": "Autorizaciones para instalación de software externo",
        "clause": "Anexo A",
        "annex": "8.19",
        "description": "Software de terceros que se puede instalar, para quién, quién lo autorizó y si sigue en uso.",
        "source": "01 - Autorizaciones para instalación de software externo.xlsx",
        "title": "AUTORIZACIONES PARA INSTALACIÓN DE SOFTWARE EXTERNO",
        "by_year": False,
        "layout": "list",
        "sections": [
            {
                "key": "software",
                "label": "Software autorizado",
                "sheet": "Hoja 1",
                "fields": [
                    {"key": "software", "label": "Software externo", "type": "text",
                     "aliases": ["software externo"], "required": True},
                    {"key": "alcance", "label": "Persona, perfil de cargo o área", "type": "text",
                     "aliases": ["persona, perfil de cargo", "persona", "perfil de cargo"]},
                    {"key": "fecha", "label": "Fecha de autorización", "type": "date",
                     "aliases": ["fecha de autorizacion"]},
                    {"key": "autorizado_por", "label": "Autorizado por", "type": "text", "aliases": ["autorizado por"]},
                    {"key": "estado", "label": "Estado", "type": "choice", "aliases": ["estado"], "default": "En uso",
                     "choices": ["En uso", "En desuso"]},
                ],
            },
        ],
    },
    "obligaciones-ose": {
        "name": "Requisitos y obligaciones del OSE",
        "clause": "4.2",
        "annex": "5.31",
        "description": "Requisitos de inscripción (artículos 5 y 6) y obligaciones del Operador de Servicios "
                       "Electrónicos (artículo 7) de la R.S. N.° 117-2017/SUNAT, con su control y responsable.",
        "source": "OSI4 - Listado de requisitos y obligaciones del OSE_<año>.xlsx",
        "title": "LISTADO DE REQUISITOS Y OBLIGACIONES DEL OSE {year}",
        "by_year": True,
        "layout": "checklist",
        "sections": [
            {
                "key": "requisitos",
                "label": "Requisitos y obligaciones",
                "group_by": "articulo",
                "fields": [
                    {"key": "articulo", "label": "Artículo", "type": "choice",
                     "choices": ["Artículo 5", "Artículo 6", "Artículo 7"]},
                    {"key": "numeral", "label": "Numeral", "type": "text"},
                    {"key": "obligacion", "label": "Requisito u obligación", "type": "longtext", "required": True},
                    {"key": "cumple", "label": "¿Cumple?", "type": "choice", "choices": ["Sí", "No", "Por revisar"],
                     "default": "Por revisar"},
                    {"key": "control", "label": "Control para el cumplimiento", "type": "text"},
                    {"key": "responsable", "label": "Responsable del cumplimiento", "type": "text"},
                ],
            },
        ],
    },
    "librerias-externas": {
        "name": "Inventario de librerías externas autorizadas",
        "clause": "Anexo A",
        "annex": "8.28",
        "description": "Librerías y componentes de terceros que el área de Desarrollo puede usar en el ERP, "
                       "con su proveedor o autor.",
        "source": "05 - Área de Desarrollo/02 - Programación/Registro/Inventario de librerías externas autorizadas.xlsx",
        "title": "INVENTARIO DE LIBRERÍAS EXTERNAS AUTORIZADAS",
        "by_year": False,
        "layout": "table",
        "sections": [
            {
                "key": "librerias",
                "label": "Librerías",
                "sheet": "Hoja 1",
                "fields": [
                    {"key": "libreria", "label": "Nombre de librería", "type": "text",
                     "aliases": ["nombre de libreria"], "required": True},
                    {"key": "proveedor", "label": "Proveedor o autor", "type": "text", "aliases": ["proveedor/autor", "proveedor"]},
                    {"key": "uso", "label": "Uso en el sistema", "type": "text", "aliases": ["uso"]},
                    {"key": "estado", "label": "Estado", "type": "choice", "default": "Autorizada",
                     "choices": ["Autorizada", "En revisión", "Retirada"], "aliases": ["estado"]},
                ],
            },
        ],
    },
    "creacion-usuarios": {
        "name": "Registro de creación de usuarios",
        "clause": "Anexo A",
        "annex": "5.16 y 5.18",
        "description": "Cuentas creadas para cada colaborador: licencias, correo, quién lo autorizó y cuándo.",
        "source": "06 - Área de Producción/03 - Infraestructura Tecnológica/Registros/01 - Creación de usuarios.xlsx",
        "title": "REGISTRO DE CREACIÓN DE USUARIOS {year}",
        "by_year": True,
        "layout": "table",
        "sections": [
            {
                "key": "usuarios",
                "label": "Usuarios creados",
                "fields": [
                    {"key": "colaborador", "label": "Colaborador", "type": "text", "aliases": ["colaborador"], "required": True},
                    {"key": "perfil", "label": "Perfil de puesto", "type": "text", "aliases": ["perfil de puesto"]},
                    {"key": "licencias", "label": "Licencias", "type": "text", "aliases": ["licencias"]},
                    {"key": "correo", "label": "Dirección de correo", "type": "text", "aliases": ["direccion de correo", "correo"]},
                    {"key": "autorizador", "label": "Autorizador", "type": "text", "aliases": ["autorizador"]},
                    {"key": "fecha", "label": "Fecha de creación", "type": "date", "aliases": ["fecha creacion", "fecha de creacion"]},
                    {"key": "comentario", "label": "Comentario", "type": "longtext", "aliases": ["comentario"]},
                ],
            },
        ],
    },
    "actas-borrado": {
        "name": "Actas de borrado y destrucción de registros",
        "clause": "Anexo A",
        "annex": "7.14 y 8.10",
        "description": "Cada soporte que se borró o destruyó: qué equipo o información, cuándo, con qué método y quién lo hizo.",
        "source": "02 - Área de Seguridad / Registros / Actas de Borrado / <año> / *.docx",
        "title": "ACTAS DE BORRADO Y DESTRUCCIÓN DE REGISTROS {year}",
        "by_year": True,
        "layout": "table",
        "accept": [".zip", ".docx", ".xlsx"],
        "import_hint": "Suba la carpeta «Actas de Borrado» comprimida en ZIP (con sus actas en Word) o un acta suelta. Cada acta se ubica en el año de su fecha.",
        "sections": [
            {
                "key": "actas",
                "label": "Actas",
                "fields": [
                    {"key": "soporte", "label": "Soporte borrado o destruido", "type": "text", "required": True},
                    {"key": "fecha", "label": "Fecha", "type": "date"},
                    {"key": "metodo", "label": "Método", "type": "text"},
                    {"key": "responsable", "label": "Responsable", "type": "text"},
                    {"key": "archivo", "label": "Acta original", "type": "text"},
                ],
            },
        ],
    },
    "actas-reunion": {
        "name": "Actas de reunión del SGSI",
        "clause": "9.3 y 10.2",
        "annex": "5.4",
        "description": "Reuniones del SGSI con su objetivo, asistentes y acuerdos, para dar seguimiento a lo que se decidió.",
        "source": "02 - Área de Seguridad / Registros / Actas de Reunión / <año> / *.docx",
        "title": "ACTAS DE REUNIÓN DEL SGSI {year}",
        "by_year": True,
        "layout": "table",
        "accept": [".zip", ".docx", ".xlsx"],
        "import_hint": "Suba la carpeta «Actas de Reunión» comprimida en ZIP o un acta suelta en Word. Se leen asunto, fecha, lugar, asistentes y acuerdos.",
        "sections": [
            {
                "key": "reuniones",
                "label": "Reuniones",
                "fields": [
                    {"key": "numero", "label": "N.° de reunión", "type": "text"},
                    {"key": "fecha", "label": "Fecha", "type": "date"},
                    {"key": "asunto", "label": "Asunto", "type": "longtext", "required": True},
                    {"key": "lugar", "label": "Lugar", "type": "text"},
                    {"key": "asistentes", "label": "Asistentes", "type": "longtext"},
                    {"key": "acuerdos", "label": "Acuerdos", "type": "longtext"},
                    {"key": "estado", "label": "Estado", "type": "choice", "default": "Pendientes",
                     "choices": ["Pendientes", "En curso", "Cumplidos"]},
                ],
            },
        ],
    },
    "copias-respaldo": {
        "name": "Cuadro de copias de respaldo",
        "clause": "Anexo A",
        "annex": "8.13",
        "description": "Qué activos se respaldan, con qué frecuencia se copian y cada cuánto se prueba que la copia se puede restaurar.",
        "source": "02 - Área de Seguridad / Registros / LOG Copias de seguridad / Copias de Respaldo - 2022.xlsx",
        "title": "CUADRO DE COPIAS DE RESPALDO",
        "by_year": False,
        "layout": "table",
        "sections": [
            {
                "key": "activos",
                "label": "Activos respaldados",
                "fields": [
                    {"key": "activo", "label": "Activo", "type": "text", "aliases": ["activos", "activo"], "required": True},
                    {"key": "frecuencia_copia", "label": "Frecuencia de copias", "type": "longtext", "aliases": ["frecuencia de copias"]},
                    {"key": "frecuencia_prueba", "label": "Frecuencia de prueba de copias", "type": "longtext",
                     "aliases": ["frecuencia de prueba"]},
                    {"key": "responsable", "label": "Responsable", "type": "text", "aliases": ["responsable"]},
                ],
            },
        ],
    },
    "cambio-claves": {
        "name": "Registro de cambio de claves",
        "clause": "Anexo A",
        "annex": "5.17",
        "description": "En qué meses se cambió la clave de cada cuenta privilegiada o compartida. "
                       "Solo se guarda el mes del cambio: las claves nunca se registran en el sistema.",
        "source": "02 - Área de Seguridad / Registros / LOG Gestión de Claves / Registro de cambio de claves.xlsx",
        "title": "REGISTRO DE CAMBIO DE CLAVES {year}",
        "by_year": True,
        "layout": "table",
        "import_hint": "Al importar el Excel original solo se lee si cada mes tiene un cambio; el contenido de las celdas no se lee ni se guarda. "
                       "Ese Excel tiene claves escritas: después de importarlo, conviene retirarlo de SharePoint.",
        "sections": [
            {
                "key": "cuentas",
                "label": "Cuentas",
                "fields": [
                    {"key": "cuenta", "label": "Cuenta", "type": "text", "required": True},
                    {"key": "tipo", "label": "Tipo", "type": "choice",
                     "choices": ["Supremo", "Directorio activo", "AnyDesk", "Dispositivo", "Otra"], "default": "Otra"},
                    {"key": "meses", "label": "Meses con cambio", "type": "months"},
                    {"key": "observacion", "label": "Observación", "type": "text"},
                ],
            },
        ],
    },
}


# ------------------------------------------------------------------------------------------
# Registros de «02 - Área de Seguridad / Registros» (01 a 18), incidentes y medidas correctivas.
# Se declaran de forma compacta: (clave, etiqueta, tipo, alias del encabezado en el Excel, obligatorio).

def _f(key, label, kind="text", aliases=(), required=False, choices=None, default=""):
    field = {"key": key, "label": label, "type": kind, "aliases": list(aliases)}
    if required:
        field["required"] = True
    if choices:
        field["choices"] = choices
    if default:
        field["default"] = default
    return field


def _reg(name, annex, description, source, fields, clause="Anexo A", by_year=False, group="Operación",
         sheets="first", sheet_field=None, year_from="sheet", ok=None, title=None):
    section = {"key": "filas", "label": name, "fields": fields, "sheets": sheets, "year_from": year_from}
    if sheet_field:
        section["sheet_field"] = sheet_field
    return {
        "name": name, "clause": clause, "annex": annex, "description": description,
        "source": f"02 - Área de Seguridad / Registros / {source}",
        "title": (title or name.upper()) + (" {year}" if by_year else ""),
        "by_year": by_year, "layout": "table", "group": group, "ok": ok, "sections": [section],
    }


EXTRA_REGISTERS = {
    "retiro-activos": _reg(
        "Autorizaciones para retirar activos fuera de las instalaciones", "7.9 y 7.10",
        "Equipos que salen de la oficina: quién los lleva, quién autorizó, en qué plazo vuelven y si ya volvieron.",
        "02 - Autorizaciones para retirar activos fuera de las instalaciones.xlsx",
        [_f("activo", "Activo", aliases=["activo"], required=True),
         _f("trabajador", "Trabajador", aliases=["nombre completo del trabajador", "trabajador"]),
         _f("fecha", "Fecha de autorización", "date", ["fecha de autorizacion"]),
         _f("plazo", "Plazo de retorno", aliases=["plazo de retorno"]),
         _f("retorno", "Fecha de retorno", "date", ["fecha de retorno"]),
         _f("autorizado_por", "Autorizado por", aliases=["autorizado por"]),
         _f("medio", "Medio", aliases=["medio"])],
        group="Activos y equipos", sheets=["Hoja 1"],
        ok={"field": "retorno", "label": "Ya retornaron", "rest": "Sin retorno registrado"}),
    "paginas-internet": _reg(
        "Autorización para acceder a determinadas páginas de Internet", "8.23",
        "Sitios web permitidos fuera del filtro general, para quién y quién lo autorizó.",
        "03 - Autorización para acceder a determinadas páginas de Internet.xlsx",
        [_f("url", "Página de Internet (URL)", aliases=["pagina de internet"], required=True),
         _f("alcance", "Persona, perfil de cargo o área", aliases=["persona, perfil de cargo", "persona"]),
         _f("fecha", "Fecha de autorización", "date", ["fecha de autorizacion"]),
         _f("autorizado_por", "Autorizado por", aliases=["autorizado por"]),
         _f("observacion", "Observación", aliases=["observacion"])],
        group="Control de acceso"),
    "intercambio-datos": _reg(
        "Decisión sobre cómo intercambiar cada tipo de dato", "5.14",
        "Para cada tipo de dato, el medio aprobado para intercambiarlo con terceros.",
        "04 - Decisión acerca de como se puede intercambiar cada tipo de dato.xlsx",
        [_f("tipo_dato", "Tipo de dato", aliases=["tipo de dato"], required=True),
         _f("detalle", "Cómo se intercambia", "longtext", ["detalle de como"]),
         _f("fecha", "Fecha de aprobación", "date", ["fecha de aprobacion"]),
         _f("aprobado_por", "Aprobado por", aliases=["aprobado por"]),
         _f("estado", "Estado", aliases=["estado"])],
        group="Información y comunicaciones"),
    "almacenamiento-mensajes": _reg(
        "Decisión sobre cómo almacenar mensajes con datos importantes", "5.14 y 5.33",
        "Dónde y cómo se guardan los mensajes que contienen datos importantes para el negocio.",
        "05 - Decisión acerca de cómo se deben almacenar los mensajes que contienen datos importantes para el negocio.xlsx",
        [_f("tipo_mensaje", "Tipo de mensaje", aliases=["tipo de mensaje"], required=True),
         _f("detalle", "Cómo se almacena", "longtext", ["detalle de como"]),
         _f("fecha", "Fecha de aprobación", "date", ["fecha de aprobacion"]),
         _f("aprobado_por", "Aprobado por", aliases=["aprobado por"])],
        group="Información y comunicaciones"),
    "byod-personas": _reg(
        "Personas autorizadas a usar dispositivos propios (BYOD)", "6.7 y 8.1",
        "Quién puede trabajar con su propio dispositivo, a qué puede acceder y a qué no.",
        "06 - Lista de cargos a quienes se les permite utilizar BYOD.xlsx",
        [_f("trabajador", "Trabajador", aliases=["trabajador"], required=True),
         _f("cargo", "Cargo", aliases=["cargo"]),
         _f("area", "Área", aliases=["area"]),
         _f("puede", "Puede acceder a", "longtext", ["¿a que puede acceder"]),
         _f("no_puede", "No puede acceder a", "longtext", ["¿a que no puede"]),
         _f("estado", "Estado", "choice", ["estado"], choices=["Activo", "Baja"], default="Activo")],
        group="Dispositivos y teletrabajo", ok={"field": "estado", "values": ["Activo"], "label": "Activos", "rest": "De baja"}),
    "byod-dispositivos": _reg(
        "Dispositivos aceptados como BYOD", "8.1",
        "Equipos personales autorizados: de quién son, qué equipo es y desde cuándo.",
        "07 - Lista de dispositivos aceptados que pueden ser utilizados como BYOD.xlsx",
        [_f("trabajador", "Trabajador", aliases=["trabajador"], required=True),
         _f("cargo", "Cargo", aliases=["cargo"]),
         _f("area", "Área", aliases=["area"]),
         _f("equipo", "Equipo", aliases=["equipo"]),
         _f("descripcion", "Descripción", "longtext", ["descripcion"]),
         _f("fecha", "Fecha de autorización", "date", ["fecha autorizacion", "fecha de autorizacion"]),
         _f("observacion", "Observación", aliases=["observacion"]),
         _f("estado", "Estado", aliases=["estado"])],
        group="Dispositivos y teletrabajo"),
    "byod-apps-prohibidas": _reg(
        "Aplicaciones prohibidas para BYOD", "8.1 y 8.19",
        "Aplicaciones que no se pueden tener en un dispositivo propio que accede a información de la empresa.",
        "08 - Lista de aplicaciones prohibidas para BYOD.xlsx",
        [_f("aplicacion", "Aplicación", aliases=["nombre de aplicacion"], required=True),
         _f("fabricante", "Fabricante", aliases=["fabricante"]),
         _f("sistema", "Sistema operativo", aliases=["sistema operativo"]),
         _f("motivo", "Motivo de la prohibición", "longtext", ["motivos de prohibicion"])],
        group="Dispositivos y teletrabajo"),
    "teletrabajo": _reg(
        "Autorización para teletrabajo", "6.7",
        "Personas autorizadas a teletrabajar, con qué dispositivo y en qué condiciones.",
        "09 - Autorización para tele-trabajo.xlsx",
        [_f("persona", "Persona autorizada / cargo", aliases=["persona autorizada"], required=True),
         _f("dispositivo", "Dispositivo autorizado", aliases=["dispositivo autorizado"]),
         _f("detalles", "Detalles del teletrabajo", "longtext", ["detalles de tele"]),
         _f("fecha", "Fecha de autorización", "date", ["fecha de autorizacion"]),
         _f("autorizado_por", "Autorizado por", aliases=["autorizado por"]),
         _f("estado", "Estado", aliases=["estado"]),
         _f("comentario", "Comentario", aliases=["comentario"])],
        group="Dispositivos y teletrabajo"),
    "acceso-restringidos": _reg(
        "Personas autorizadas a documentos RESTRINGIDA y CONFIDENCIAL", "5.12 y 5.15",
        "Qué cargos pueden abrir cada documento o instructivo clasificado como restringido o confidencial.",
        "10 - Lista de personas autorizadas para acceder a documentos clasificados como RESTRINGIDA Y CONFIDENCIAL.xlsx",
        [_f("tipo", "Tipo", aliases=["tipo"]),
         _f("archivo", "Nombre del archivo", aliases=["nombre del archivo"], required=True),
         _f("ruta", "Ruta del archivo", aliases=["ruta de archivo"]),
         _f("fecha", "Fecha de aprobación", "date", ["f aprob"]),
         _f("cargos", "Cargos autorizados", "longtext", ["cargos autorizados"])],
        group="Control de acceso", sheets=["Documentos", "Instructivos"], sheet_field="tipo"),
    "correo-entrante": _reg(
        "Registro de correo entrante", "5.14",
        "Documentos físicos o electrónicos recibidos: remitente, fecha y a quién se entregaron.",
        "11 - Registro de correo entrante.xlsx",
        [_f("nro", "N.° de documento", aliases=["nro de documento"]),
         _f("remitente", "Remitente", aliases=["remitente"], required=True),
         _f("descripcion", "Descripción", "longtext", ["descripcion"]),
         _f("fecha", "Fecha de recepción", "date", ["fecha de recepcion"]),
         _f("destinatario", "Entregado a", aliases=["nombre de la persona"]),
         _f("tipo", "Tipo de correo", aliases=["tipo de correo"])],
        by_year=True, sheets="all", group="Información y comunicaciones"),
    "cuentas-grupales": _reg(
        "Responsables de cuentas grupales", "5.16",
        "Cuentas compartidas por varias personas, con su responsable y quiénes la usan.",
        "12 - Lista de responsables para cuentas grupales.xlsx",
        [_f("nro", "N.° de documento", aliases=["nro de documento"]),
         _f("cuenta", "Usuario o cuenta", aliases=["nombre de usuario"], required=True),
         _f("sistema", "Sistema o aplicación", aliases=["sistema aplicacion", "sistema"]),
         _f("responsable", "Responsable", aliases=["responsable"]),
         _f("usuarios", "Usuarios", "longtext", ["usuarios"]),
         _f("fecha", "Fecha de autorización", "date", ["fecha de autorizacion"]),
         _f("estado", "Estado", aliases=["estado"])],
        group="Control de acceso"),
    "retencion-registros": _reg(
        "Registros del SGSI y su tiempo de retención", "5.33",
        "Cada registro del SGSI con su propietario y el tiempo que debe conservarse.",
        "13 - Lista de activos de información de SIEMPRESOFT.xlsx",
        [_f("nro", "N.°", aliases=["n°", "n"]),
         _f("documento", "Registro", aliases=["nombre del documento"], required=True),
         _f("propietario", "Propietario", aliases=["propietario"]),
         _f("retencion", "Tiempo de retención", aliases=["tiempo de retencion"])],
        group="Información y comunicaciones"),
    "pruebas-backups": _reg(
        "Registro de pruebas de backups", "8.13",
        "Pruebas de restauración: qué información se probó, de qué área y cuándo.",
        "15 - Registro de pruebas de backups.xlsx",
        [_f("informacion", "Archivo de información", aliases=["archivo de informacion"], required=True),
         _f("archivo", "Nombre del archivo", aliases=["nombre del archivo"]),
         _f("area", "Área / perfil de puesto", aliases=["area perfil", "area"]),
         _f("fecha", "Fecha de subida", "date", ["fecha de subida"])],
        group="Operación"),
    "registro-accesos": _reg(
        "Registro de accesos por puesto", "5.15 y 5.18",
        "Qué acceso tiene cada puesto en cada sistema, con qué nivel, por qué y si está revisado.",
        "16 - Registro de accesos.xlsx",
        [_f("id", "ID", aliases=["id registro"]),
         _f("puesto", "Puesto", aliases=["puesto"], required=True),
         _f("sistema", "Sistema", aliases=["sistema"]),
         _f("justificacion", "Justificación", "longtext", ["justificacion"]),
         _f("nivel", "Nivel de acceso", aliases=["nivel de acceso"]),
         _f("cuenta", "Cuenta o usuario", aliases=["cuenta usuario", "cuenta"]),
         _f("estado", "Estado", "choice", ["estado"], choices=["Por revisar", "Vigente", "Revocado"], default="Por revisar"),
         _f("actualizacion", "Última actualización", "date", ["ultima actualizacion"]),
         _f("observaciones", "Observaciones", aliases=["observaciones"])],
        group="Control de acceso", sheets=["Registro"],
        ok={"field": "estado", "values": ["Vigente"], "label": "Revisados y vigentes", "rest": "Por revisar o revocados"}),
    "registro-permisos": _reg(
        "Registro de permisos por sistema", "5.18",
        "Permisos otorgados a cada colaborador en el repositorio de documentos, Supremo, GlobalSecure, VPN y Microsoft 365.",
        "16 - Registro de permisos.xlsx",
        [_f("ambito", "Ámbito", aliases=["ambito"]),
         _f("colaborador", "Colaborador", aliases=["colaborador"], required=True),
         _f("area", "Área / perfil de puesto", aliases=["area perfil", "area"]),
         _f("nivel", "Nivel de permiso", aliases=["nivel de permiso"]),
         _f("carpeta", "Carpeta de acceso", aliases=["carpeta de acceso"]),
         _f("direccion", "Dirección (correo)", aliases=["direccion"]),
         _f("fecha", "Fecha de permiso", "date", ["fecha de permiso", "fecha de asignacion"]),
         _f("retiro", "Fecha de retiro", "date", ["fecha de retiro"]),
         _f("condicion", "Condición", aliases=["condicion"])],
        group="Control de acceso", sheets="all", sheet_field="ambito",
        ok={"field": "retiro", "empty": True, "label": "Permisos vigentes", "rest": "Retirados"}),
    "registro-cambios": _reg(
        "Registro de cambios", "8.32",
        "Solicitudes de cambio sobre los activos: quién lo pidió, por qué y quién lo aprobó.",
        "17 - Registro de cambios.xlsx",
        [_f("solicitante", "Solicitante (perfil de puesto)", aliases=["solicitante"], required=True),
         _f("fecha_solicitud", "Fecha de solicitud", "date", ["fecha solicitud"]),
         _f("activo", "Activo", aliases=["activo"]),
         _f("justificacion", "Justificación", "longtext", ["justificacion"]),
         _f("aprobado_por", "Aprobado por", aliases=["aprobado por"]),
         _f("fecha_aprobacion", "Fecha de aprobación", "date", ["fecha aprobacion"])],
        by_year=True, sheets="all", year_from="fecha_solicitud", group="Operación",
        ok={"field": "aprobado_por", "label": "Aprobados"}),
    "comunicacion-partes": _reg(
        "Autorización de comunicación con las partes interesadas", "5.5 y 5.6", clause="7.4",
        description="Qué se comunica, cuándo, quién lo comunica, a quién y por qué medio.",
        source="18 - Autorización de comunicación con las partes interesadas.xlsx",
        fields=[_f("que", "Qué comunicar", "longtext", ["que comunicar"], required=True),
                _f("cuando", "Cuándo", "longtext", ["cuando comunicar"]),
                _f("quien", "Quién comunica", aliases=["quien debe comunicar"]),
                _f("a_quien", "A quién", aliases=["a quien comunicar"]),
                _f("proceso", "Proceso para la comunicación", "longtext", ["proceso para la comunicacion"]),
                _f("tipo", "Tipo de comunicación", aliases=["tipo de comunicacion"]),
                _f("observacion", "Observación", aliases=["observacion"])],
        group="Información y comunicaciones"),
    "registro-incidentes": _reg(
        "Registro de incidentes de seguridad de la información", "5.24 a 5.28",
        "Cada incidente reportado (RISI): fecha, responsable, cierre, tiempo de atención, acción tomada y control afectado.",
        "Incidentes del SGSI / 02 - Registro de incidentes de seguridad de la información.xlsx",
        [_f("criterio", "Criterio", aliases=["criterio"]),
         _f("nro", "N.° de reporte", aliases=["nro reporte"]),
         _f("fecha", "Fecha del incidente", "date", ["fecha del incidente"]),
         _f("descripcion", "Descripción", "longtext", ["breve descripcion"], required=True),
         _f("responsable", "Responsable", aliases=["persona responsable"]),
         _f("formulario", "Formulario", aliases=["referencia al formulario"]),
         _f("cierre", "Fecha de cierre", "date", ["fecha cierre"]),
         _f("tiempo", "Tiempo de atención", aliases=["tiempo de atencion"]),
         _f("estado", "Estado", aliases=["estado del incidente"]),
         _f("accion", "Acción tomada", "longtext", ["accion tomada"]),
         _f("control", "Control afectado", aliases=["control afectado"])],
        by_year=True, sheets="all", group="Incidentes y mejora",
        ok={"field": "cierre", "label": "Cerrados", "rest": "Sin fecha de cierre"}),
    "debilidades-eventos": _reg(
        "Registro de debilidades o eventos de seguridad", "6.8",
        "Debilidades y eventos que reporta el personal, antes de que se conviertan en incidentes.",
        "Incidentes del SGSI / 01 - Registros de debilidades o eventos de seguridad.xlsx",
        [_f("nro", "N.°", aliases=["nro"]),
         _f("responsable", "Reportado por", aliases=["responsable"]),
         _f("area", "Área / perfil", aliases=["area perfil", "area"]),
         _f("debilidad", "Debilidad o evento", "longtext", ["debilidad o evento", "incidente o debilidad", "incidente"], required=True),
         _f("fecha", "Fecha", "date", ["fecha"]),
         _f("evidencia", "Enlaces de evidencia", aliases=["enlaces de evidencia"]),
         _f("control", "Control del Anexo A", aliases=["id"])],
        by_year=True, sheets="all", group="Incidentes y mejora"),
    "medidas-correctivas": _reg(
        "Registro centralizado de medidas correctivas y mejoras", "10.2", clause="10.1 y 10.2",
        description="No conformidades, observaciones y oportunidades de mejora con su responsable, costo, formulario y estado.",
        source="Medidas correctivas / 01 - Registro centralizado de Medidas correctivas y mejoras.xlsx",
        fields=[_f("nro", "N.°", aliases=["nro"]),
                _f("fecha", "Fecha de identificación", "date", ["fecha de identificacion"]),
                _f("tipo", "Origen", aliases=["tipo"]),
                _f("descripcion", "No conformidad u observación", "longtext", ["breve descripcion"], required=True),
                _f("responsable", "Responsable", aliases=["persona responsable"]),
                _f("detalle", "Descripción detallada", "longtext", ["descripcion detallada"]),
                _f("costo", "Costo (S/)", aliases=["costo en soles"]),
                _f("costo_hh", "Costo hora/hombre", aliases=["costo hora"]),
                _f("formulario", "Formulario", aliases=["referencia al formulario"]),
                _f("atraso", "Días de atraso", aliases=["dias de atraso"]),
                _f("estado", "Estado", aliases=["estado de la medida"])],
        by_year=True, sheets="all", year_from="fecha", group="Incidentes y mejora",
        ok={"field": "estado", "values": ["Implementado", "Implementada", "Cerrado", "Cerrada"], "label": "Implementadas"}),
}
REGISTERS.update(EXTRA_REGISTERS)

GROUPS = [
    "Personas y capacitación", "Control de acceso", "Dispositivos y teletrabajo", "Activos y equipos",
    "Información y comunicaciones", "Operación", "Incidentes y mejora", "Cumplimiento",
]
for _slug, _group in {
    "plan-capacitacion": "Personas y capacitación", "software-autorizado": "Activos y equipos",
    "obligaciones-ose": "Cumplimiento", "librerias-externas": "Operación", "creacion-usuarios": "Control de acceso",
    "actas-borrado": "Activos y equipos", "actas-reunion": "Incidentes y mejora", "copias-respaldo": "Operación",
    "cambio-claves": "Control de acceso",
}.items():
    REGISTERS[_slug]["group"] = _group


def generic_summary(schema, entries):
    """Indicadores para los registros de tabla: total, cuántos cumplen la condición «ok» y el resto."""
    total = len(entries)
    ok = schema.get("ok")
    if not ok:
        return {"cards": [{"label": "Filas", "value": total}], "progress": 100 if total else 0}
    field = ok["field"]
    if ok.get("empty"):
        good = sum(1 for e in entries if not e.data.get(field))
    elif ok.get("values"):
        wanted = {v.lower() for v in ok["values"]}
        good = sum(1 for e in entries if str(e.data.get(field, "")).strip().lower() in wanted)
    else:
        good = sum(1 for e in entries if e.data.get(field))
    return {
        "cards": [
            {"label": "Filas", "value": total},
            {"label": ok["label"], "value": good},
            {"label": ok.get("rest", "Pendientes"), "value": total - good},
        ],
        "progress": round(100 * good / total) if total else 0,
    }


def get(slug):
    return REGISTERS.get(slug)


def section(schema, key):
    return next((s for s in schema["sections"] if s["key"] == key), schema["sections"][0])


def clean_value(field, value):
    """Normaliza lo que llega del formulario o del Excel según el tipo de campo."""
    kind = field["type"]
    if kind == "months":
        if isinstance(value, str):
            value = [v for v in value.split(",") if v.strip()]
        months = sorted({int(m) for m in (value or []) if str(m).isdigit() and 1 <= int(m) <= 12})
        return months
    if value is None:
        return ""
    value = str(value).strip()
    if kind == "date" and value:
        import re
        m = re.match(r"\s*(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b", value)
        if m:
            return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
        return value[:10]
    if kind == "choice" and value:
        for choice in field.get("choices", []):
            if choice.lower() == value.lower():
                return choice
    return value


def summary(slug, entries):
    """Indicadores que se muestran sobre el registro."""
    if slug == "plan-capacitacion":
        total = len(entries)
        done = sum(1 for e in entries if e.data.get("estado") == "Realizada")
        by_month = [0] * 12
        for e in entries:
            for m in e.data.get("meses", []):
                by_month[m - 1] += 1
        peak = max(by_month) if total else 0
        return {
            "cards": [
                {"label": "Temas programados", "value": total},
                {"label": "Realizados", "value": done, "hint": f"{round(100 * done / total) if total else 0} %"},
                {"label": "Perfiles de puesto", "value": len({e.data.get('perfil') for e in entries if e.data.get('perfil')})},
            ],
            "months": [{"label": MONTHS[i], "count": c, "pct": round(100 * c / peak) if peak else 0} for i, c in enumerate(by_month)],
            "progress": round(100 * done / total) if total else 0,
        }
    if slug == "software-autorizado":
        total = len(entries)
        in_use = sum(1 for e in entries if e.data.get("estado") == "En uso")
        return {
            "cards": [
                {"label": "Software registrado", "value": total},
                {"label": "En uso", "value": in_use},
                {"label": "En desuso", "value": total - in_use},
            ],
            "progress": round(100 * in_use / total) if total else 0,
        }
    if slug == "obligaciones-ose":
        items = [e for e in entries if e.data.get("tipo") != "grupo"]
        ok = sum(1 for e in items if e.data.get("cumple") == "Sí")
        no = sum(1 for e in items if e.data.get("cumple") == "No")
        return {
            "cards": [
                {"label": "Cumple", "value": ok},
                {"label": "No cumple", "value": no},
                {"label": "Por revisar", "value": len(items) - ok - no},
            ],
            "progress": round(100 * ok / len(items)) if items else 0,
        }
    if slug == "librerias-externas":
        total = len(entries)
        ok = sum(1 for e in entries if e.data.get("estado") == "Autorizada")
        return {
            "cards": [
                {"label": "Librerías registradas", "value": total},
                {"label": "Autorizadas", "value": ok},
                {"label": "Proveedores", "value": len({e.data.get("proveedor") for e in entries if e.data.get("proveedor")})},
            ],
            "progress": round(100 * ok / total) if total else 0,
        }
    if slug == "creacion-usuarios":
        total = len(entries)
        authorized = sum(1 for e in entries if e.data.get("autorizador"))
        return {
            "cards": [
                {"label": "Usuarios creados", "value": total},
                {"label": "Con autorizador", "value": authorized},
                {"label": "Sin autorizador", "value": total - authorized},
            ],
            "progress": round(100 * authorized / total) if total else 0,
        }
    if slug == "actas-borrado":
        total = len(entries)
        signed = sum(1 for e in entries if e.data.get("responsable"))
        return {
            "cards": [
                {"label": "Actas", "value": total},
                {"label": "Con responsable", "value": signed},
                {"label": "Métodos distintos", "value": len({e.data.get("metodo") for e in entries if e.data.get("metodo")})},
            ],
            "progress": round(100 * signed / total) if total else 0,
        }
    if slug == "actas-reunion":
        total = len(entries)
        done = sum(1 for e in entries if e.data.get("estado") == "Cumplidos")
        return {
            "cards": [
                {"label": "Reuniones", "value": total},
                {"label": "Acuerdos cumplidos", "value": done},
                {"label": "Con acuerdos por cerrar", "value": total - done},
            ],
            "progress": round(100 * done / total) if total else 0,
        }
    if slug == "copias-respaldo":
        total = len(entries)
        tested = sum(1 for e in entries if (e.data.get("frecuencia_prueba") or "").strip() not in ("", "-"))
        return {
            "cards": [
                {"label": "Activos respaldados", "value": total},
                {"label": "Con prueba de restauración", "value": tested},
                {"label": "Sin frecuencia definida", "value": sum(1 for e in entries if not e.data.get("frecuencia_copia"))},
            ],
            "progress": round(100 * tested / total) if total else 0,
        }
    if slug == "cambio-claves":
        total = len(entries)
        changed = sum(1 for e in entries if e.data.get("meses"))
        return {
            "cards": [
                {"label": "Cuentas", "value": total},
                {"label": "Cuentas con cambio en el año", "value": changed},
                {"label": "Cambios registrados", "value": sum(len(e.data.get("meses", [])) for e in entries)},
            ],
            "progress": round(100 * changed / total) if total else 0,
        }
    schema = REGISTERS.get(slug)
    if schema:
        return generic_summary(schema, entries)
    return {"cards": [], "progress": 0}
