from pathlib import Path
from unittest import skipUnless

from django.conf import settings

ACTIVOS = "apps/assets/data/siempresoft_activos.json"
REGISTROS = "apps/registers/data/registros_siempresoft.json"
DOCUMENTOS = "apps/dashboard/data/documentos/manifiesto.json"
TABLERO_2026 = "apps/dashboard/data/documentos/Dashboard SGSI de SIEMPRESOFT_2026.xlsx"
MATRIZ_2026 = "apps/traceability/data/Matriz_Identificacion_Valoracion_Riesgos_SiempreSoft_2026.xlsx"


def requiere_datos_reales(*rutas):
    faltan = [ruta for ruta in rutas if not (Path(settings.BASE_DIR) / ruta).exists()]
    return skipUnless(not faltan, "Datos reales de SiempreSoft no incluidos: " + ", ".join(faltan))
