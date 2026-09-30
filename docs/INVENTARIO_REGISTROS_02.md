# 02 / Registros, incidentes y medidas correctivas (30/09/2026)

Con los ZIP 7 y 10 y los 17 Excel de la raíz de «Registros», la carpeta 02 queda completa. Solo falta la **11 - SGSST**.

## Registros del SGSI incorporados (v18)

Todos se importan desde el Excel original tal como está: varias hojas, títulos arriba, un año por hoja. Se editan en pantalla, se descargan con el formato de SiempreSoft y el archivo descargado se vuelve a importar sin perder nada (probado con los 20 archivos reales).

| Grupo | Registro | Filas reales | Anexo A |
|---|---|---|---|
| Control de acceso | 03 Páginas de Internet autorizadas | 85 | 8.23 |
| | 10 Personas autorizadas a documentos restringidos y confidenciales | 25 | 5.12, 5.15 |
| | 12 Responsables de cuentas grupales | 20 | 5.16 |
| | 16 Registro de accesos por puesto | 228 (todos «Por revisar») | 5.15, 5.18 |
| | 16 Registro de permisos (repositorio, Supremo, GlobalSecure, VPN, M365) | 80 (64 vigentes) | 5.18 |
| Dispositivos y teletrabajo | 06 Personas autorizadas a BYOD | 14 (2 activas) | 6.7, 8.1 |
| | 07 Dispositivos BYOD | 14 | 8.1 |
| | 08 Aplicaciones prohibidas para BYOD | 9 | 8.1, 8.19 |
| | 09 Autorización para teletrabajo | 46 | 6.7 |
| Activos y equipos | 02 Retiro de activos fuera de la oficina | 170 (26 sin retorno registrado) | 7.9, 7.10 |
| Información y comunicaciones | 04 Cómo intercambiar cada tipo de dato | 20 | 5.14 |
| | 05 Cómo almacenar mensajes importantes | 12 | 5.14, 5.33 |
| | 11 Correo entrante | 31 (2019-2026) | 5.14 |
| | 13 Registros y tiempos de retención | 73 | 5.33 |
| | 18 Comunicación con partes interesadas | 36 | cláusula 7.4 |
| Operación | 15 Pruebas de backups | 15 | 8.13 |
| | 17 Registro de cambios | 54 (2020-2026) | 8.32 |
| Incidentes y mejora | Registro de incidentes (RISI) | 93 (2019-2026; 26 sin fecha de cierre) | 5.24-5.28 |
| | Debilidades o eventos de seguridad | 212 (2019-2026) | 6.8 |
| | Registro centralizado de medidas correctivas | 363 (2019-2026; 331 implementadas) | cláusulas 10.1, 10.2 |

El registro 01 (software externo) ya existía desde la v15. El índice de «Registros del SGSI» agrupa los 29 registros por tema y tiene un buscador.

## Hallazgos en los datos

- **La hoja 2026 de medidas correctivas es una copia exacta de la de 2025:** 44 filas, todas con fechas de 2025. Cada medida se ubica por su fecha de identificación y las repetidas se descartan. En 2026 hay dos formularios (001-2026 y 002-2026) que **no están** en el registro centralizado.
- **Fechas mal digitadas:** tres medidas tienen años imposibles (2027 y 2028). Se ubican en el año de su hoja y conviene corregirlas.
- **Registro de accesos:** las 228 filas están «Por revisar». No hay evidencia de revisión de derechos de acceso (5.18).
- **Retiro de activos:** 26 salidas no tienen fecha de retorno.
- **Registro de accesos y permisos:** no contienen claves; solo nombres de cuenta y descripciones de lo que permite cada acceso.

## Relación con los módulos Incidentes y Mejoras

Los módulos «Incidentes» y «Acciones de mejora» del sistema exigen usuarios del sistema (quien reporta, responsable). Los registros de SiempreSoft traen nombres y cargos escritos. Por eso se cargan como registros del SGSI, tal como los lleva la empresa. Cuando los colaboradores tengan su usuario, se puede convertir cada fila en un incidente o una acción del módulo operativo.

Los formularios individuales (99 reportes RISI en Excel con sus evidencias, y 342 formularios de medidas en Word) son evidencia de cada fila. Se cargan con la cadena de fuentes (`import_source_inventory`) y quedan como documentos del SGSI.
