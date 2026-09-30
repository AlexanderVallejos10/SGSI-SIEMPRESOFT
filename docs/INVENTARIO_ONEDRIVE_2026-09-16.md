# Inventario de la carpeta OneDrive (16/09/2026) y su lugar en el sistema

Se revisaron los tres ZIP. Para cada tipo de información se indica si era nueva, si ya existía en el sistema o si no corresponde al SGSI.

## Nuevo: incorporado en «Registros del SGSI» (v15)

| Registro | Archivo de origen | Cláusula / Anexo A |
|---|---|---|
| Plan de capacitación y concienciación | `01 - Siempresoft/Borradores/Plan de capacitación y concienciación 2026.xlsx` (y 2021-2024) | 7.2, 7.3 / 6.3 |
| Autorizaciones para instalación de software externo | `02 - Área de Seguridad/Registros/01 - Autorizaciones para instalación de software externo.xlsx` (94 programas) | 8.19 |
| Requisitos y obligaciones del OSE | `01 - Siempresoft/Registros/2025/OSI4 - Listado de requisitos y obligaciones del OSE_2025.xlsx` (R.S. 117-2017, arts. 5, 6 y 7) | 4.2 / 5.31 |

Los tres se importan desde el propio Excel (botón «Importar Excel»), se editan en pantalla y se descargan con el formato de SiempreSoft.

## Ya existía en el sistema: se carga en su módulo, no se duplica

- **Dashboard SGSI de SIEMPRESOFT (2019-2026):** mediciones, OESI, matriz OEE vs OSI y EPI vs OSI. Van en el Dashboard en vivo.
- **Objetivos específicos y OSI1-OSI8 (2021-2026):** son las series mensuales que alimentan los OESI del dashboard: disponibilidad del ERP, instalaciones OSE, caídas por regresión, comprobantes rechazados, SLA ERP/OSE, backups y PC protegidas.
- **Lista de requisitos legales V0.15 (.xlsm):** numeral 4.1.
- **Partes interesadas V0.4:** numeral 4.2.
- **Mapa de procesos V0.14 (PDF) y V0.15 (borrador):** numeral 4.3.
- **Proceso de gestión de riesgos 2025 (carpeta 2026):** matriz de riesgos. Sus hojas «Activos primarios», «Activos de soporte», «Activos tecnológicos» y «Riesgos de proyectos» son la base del punto 2 de Karim (riesgos por activo), todavía pendiente.
- **Evaluación de riesgos de DP 2025:** matriz de riesgos, como riesgos de datos personales. Pendiente.
- **Lista de asignación de propietarios de documentos:** Responsabilidades documentales.
- **Registros de debilidades o eventos de seguridad (2021-2026):** Incidentes.
- **PDF vigentes** (Metodología V0.10, Declaración de aplicabilidad v0.10, procedimientos, políticas, certificados): cada uno en su numeral, con «Subir el documento».
- **Leyes y normas en «Externos»:** requisitos legales (4.1).

## No vigentes

Los archivos marcados «NO VIGENTE» y las versiones anteriores (V0.1…V0.14) solo sirven como historial de versiones del documento vigente. No se cargan como vigentes.

## No corresponde al SGSI (no se usa)

- `04 - Área de Soporte al cliente/Borradores/documentos jpancca/…`: binarios del ERP (.dll, .exe), reportes (.mrt) y consultas SQL.
- `Archivos CSV - Autopilot`: hashes de hardware y scripts de inscripción de equipos.
- `Claves SSH - Ubuntu demo`: **contiene claves privadas**. No deben estar en una carpeta compartida. Se recomienda rotarlas y retirarlas de OneDrive.

## No llegaron (OneDrive no los descargó)

El archivo `___All_Errors.txt` lista lo que falló. Casi todo es de `02 - Área de Seguridad de la Información/Registros`:
- registros de incidentes RISI 2020-2026 y sus evidencias;
- medidas correctivas 2019-2026;
- minutas de revisión por la dirección;
- informes de auditoría;
- registros 02 a 18: retiro de activos, páginas de Internet, BYOD, teletrabajo, accesos, cambios, pruebas de backup, entre otros;
- las carpetas «Restringida» y «Uso interno».

Hay que volver a descargarlos.

## Duplicados detectados

- `OSI1 - Incidentes del sistema SIEMPRESOFT ERP - 2026.xlsx` y `… - 20261.xlsx`: el segundo es copia del primero, con una fila menos en el resumen.
- Plan de capacitación 2022: la versión de Borradores y la de «NO VIGENTE» tienen distinto número de filas (62 y 47). Hay que confirmar cuál es la final.
- `Reporte de Incidentes … V0.2` y `V0.3 - Copia`: formato del reporte de incidentes. El V0.3 agrega la hoja «infracción».
