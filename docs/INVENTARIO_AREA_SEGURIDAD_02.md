# 02 - Área de Seguridad de la Información: análisis (30/09/2026)

Se recibieron 16 archivos: 11 ZIP de OneDrive, `Placas`, `Restringida`, `Externos`, `Formatos`, `Anexos` y el Word de la Comisión.

## Lo que llegó y si era nuevo

| Carpeta | Archivos | Estado |
|---|---|---|
| Uso interno | 189 (18 vigentes) | **Nuevo**: políticas y procedimientos del SGSI |
| Restringida | 45 (3 vigentes) | **Nuevo**: criptografía, auditoría interna y programa 2026 |
| Gestión de Riesgos | 70 | Casi todo ya estaba. **Nuevos:** matriz 2026 (52 riesgos) y riesgos de DP 2026 |
| Registros / Plan de recuperación ante desastre | 23 | **Nuevo**: plan de 2020, capturas de la prueba de 2019 y activaciones |
| Registros / LOG Copias de seguridad | 2 | **Nuevo**: pasa a registro |
| Registros / LOG Gestión de Claves | 1 | **Nuevo, con claves escritas**: solo se guarda el mes del cambio |
| Registros / Placas | 7 | **Nuevo**: fotos de las placas de CPU; van en «Activos y equipos» |
| Actas de borrado, actas de reunión, Autopilot, declaraciones | 238 | Ya estaban. Borrado y reunión pasan ahora a registros |
| Externos, Formatos, Anexos | 65 | Ya estaban |

## Nuevos registros (v17)

| Registro | Origen | Filas reales | Anexo A |
|---|---|---|---|
| Actas de borrado y destrucción | ZIP «Actas de Borrado» (Word) | 43 actas, 2019-2026 | 7.14, 8.10 |
| Actas de reunión del SGSI | ZIP «Actas de Reunión» (Word) | 30 reuniones, 2020-2026, con asistentes y acuerdos | 9.3, 10.2 |
| Cuadro de copias de respaldo | Copias de Respaldo - 2022.xlsx | 14 activos | 8.13 |
| Registro de cambio de claves | Registro de cambio de claves.xlsx | 45 cuentas, 2020-2022 | 5.17 |

Las actas se importan subiendo la carpeta comprimida tal como sale de OneDrive. Cada acta se ubica en el año de su fecha y las «- Copia» se omiten.

## Documentos vigentes y su lugar

| Documento | Numeral o control |
|---|---|
| Documento sobre el alcance del SGSI V0.13 | 4.3 |
| Política de seguridad de la información V0.12 | 5.2 / A.5.1 |
| **Manual del SGSI V0.6** | 4-10. El sistema usa el V0.7, que en el repositorio sigue como borrador: confirmar con Karim |
| Dispositivos móviles y teletrabajo V0.11 | A.6.7, A.8.1 |
| Pantalla y escritorio limpios V0.9 | A.7.7 |
| Uso aceptable V0.10 | A.5.10 |
| Eliminación y destrucción V0.8 | A.7.14, A.8.10 |
| Política de claves V0.8 | A.5.17 |
| Gestión de incidentes V0.8 | A.5.24-5.27 |
| Reglas de evidencia V0.4 | A.5.28 |
| Proceso disciplinario V0.4 | A.6.4 |
| Control de acceso V0.20 | A.5.15 |
| Clasificación de la información V0.8 | A.5.12, A.5.13 |
| Trabajo en áreas seguras V0.12 | A.7.6 |
| Copias de seguridad V0.14 | A.8.13 |
| Plan de recuperación ante desastres en oficina V0.12 | A.5.29, A.5.30 |
| Registro de funciones y contactos | A.5.5 |
| Gestión de cambio V0.7 | A.8.32 |
| Uso de controles criptográficos V0.9 (restringida) | A.8.24 |
| Procedimiento de auditoría interna V0.9 y Programa anual 2026 (restringida) | 9.2 |

## Seguridad

- **Registro de cambio de claves.xlsx:** 38 de sus celdas parecen claves escritas en texto plano. El cargador de repositorios ahora lo omite. El registro del sistema solo guarda cuenta, tipo y meses, y una prueba verifica que ninguna clave quede guardada ni se exporte. Recomendación: eliminar ese Excel de SharePoint una vez importado.
- **Carpeta «Claves SSH - Ubuntu demo»:** no vino en este envío. Sigue en SharePoint y debería retirarse.

## Todavía no ha llegado

En la numeración de OneDrive faltan los ZIP **7 y 10**. Por la lista de errores del primer envío, dentro de `Registros` faltan:
- Incidentes del SGSI (RISI 2019-2026, más de 60 reportes, y sus evidencias);
- Medidas correctivas (2019-2026, más de 90 formularios);
- Minutas de reunión y el informe de revisión por la dirección;
- Informes de auditoría y revisiones periódicas;
- los Excel 02 a 18 de la raíz de `Registros`: retiro de activos, páginas de Internet, BYOD, teletrabajo, accesos, cambios, pruebas de backup, entre otros.

Además, la **11 - SGSST**.
