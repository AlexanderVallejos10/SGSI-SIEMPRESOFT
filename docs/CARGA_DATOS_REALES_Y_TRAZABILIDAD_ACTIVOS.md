# Datos reales de SiempreSoft y trazabilidad de activos (v19)

## Qué se carga

Un solo comando carga todo lo que salió del repositorio de OneDrive de SiempreSoft:

```
docker compose exec web python manage.py cargar_datos_siempresoft
```

| Qué | Cantidad | Origen |
|---|---|---|
| Registros del SGSI (29 registros) | 1.932 filas | Excel y actas en Word de «02 - Área de Seguridad», áreas 01, 05 y 06 |
| Colaboradores | 56 | Hoja «Microsoft 365» del registro de permisos, correos del inventario, creación de usuarios y declaraciones firmadas |
| Equipos con código SS1 | 372 | Inventario de escritorios y PCs (2019, 2021, 2023, 2024, 2025, 2026) |
| Asignaciones y cambios de responsable | según el inventario de cada año | Mismo inventario |
| Salidas y retornos de la oficina | 606 | Registro 02 - Retiro de activos |
| Revisiones periódicas de seguridad | 389 | Revisión periódica 2021-2025 (tabla «Usuario / Evidencia») |
| Inventarios de software (Microsoft Defender) | 41 | ACTIVOS 07022023 y Otras revisiones / aplicaciones instaladas |
| Activos de información (primarios) | 23 | Proceso de gestión de riesgos 2026 / Activos primarios |
| Activos de soporte | 47 | Proceso de gestión de riesgos 2026 / Activos de soporte |
| Activos tecnológicos con sus riesgos | 41 | Proceso de gestión de riesgos 2026 / Activos tecnológicos |
| Bajas (borrado y destrucción) | 43 | Actas de borrado 2019-2026 |
| Dispositivos BYOD | 14 | Registro 07 |

- Se puede ejecutar varias veces: cada dato tiene una clave de importación y se actualiza, no se duplica.
- Los registros solo se llenan en los años vacíos. Con `--reemplazar`, se sobrescriben con el paquete.
- Cada activo, movimiento y revisión muestra de qué archivo sale.

## Colaboradores

Se crean como usuarios **sin acceso** al sistema: inactivos, sin contraseña y con estado «no confirmado», o «inactivo» si Microsoft 365 registra su fecha de retiro. Solo sirven para enlazarles sus equipos. Un administrador los activa desde «Usuarios y accesos» cuando corresponda.

Una misma persona escrita de distintas formas se une en un solo usuario: «Ana Karim Salazar – Oficial…», «Karim Salazar», «ksalazar@siempresoft.com» y «PC-Karim-Salazar» son la misma persona. El correo solo se une con el nombre cuando coincide sin ambigüedad, con la inicial más el apellido («avillasis» y «Angelo Villasis»).

## La ficha del activo (lo que pidió Karim)

Se entra desde **Activos y equipos** (menú) o desde el **perfil de la persona** (pestaña Activos). Cada ficha muestra:

- **Responsable actual** (enlace a su perfil), ubicación, nombre del equipo y modelo o placa.
- **Trazabilidad**, en orden de fecha:
  - quién lo tuvo cada año y cuándo cambió de responsable;
  - cada salida y retorno de la oficina, con quién lo autorizó;
  - las revisiones periódicas de seguridad con su evidencia (bloqueo USB, cifrado, actualizaciones…);
  - los inventarios de software;
  - la baja, si la hubo.
- **Resto del puesto** de esa persona: monitor, teclado, mouse, cámara…
- **Software instalado**, ordenado por debilidades conocidas, con los programas que tienen exploit público resaltados.
- Para activos de información y soporte, la **valoración C·I·D**. Para los tecnológicos, **sus riesgos** con consecuencia, probabilidad, nivel y controles.

Ejemplo real: **SS1-CPU-012** estuvo con José Torres de 2019 a 2025. En 2026 pasó a Jannyna Pancca, en Soporte al cliente. Registra 25 revisiones periódicas y 2 inventarios de software.

## Decisiones sobre los datos

- **Equipos «En revisión»:** 169 equipos no figuran en el inventario 2026. No se dan de baja automáticamente; hay que confirmar con Karim si se retiraron.
- **Números de serie de Autopilot:** no se enlazan a los códigos SS1. En la hoja del inventario los códigos van correlativos, sin relación con cada fila, y enlazarlos inventaría datos.
- **Datos que no se guardan:** IP, hashes de hardware y claves.
- **Datos sin equipo:** 37 revisiones y 4 inventarios de software no tienen un equipo identificable de esa persona en el inventario (consultores externos, laptops compartidas de consultoría). Se informan al cargar y no se asignan a ciegas.

## Si llegan archivos nuevos

El paquete se arma con dos scripts que leen los archivos originales:

```
python scripts/build_seed_siempresoft.py <carpeta con los archivos> apps/assets/data/siempresoft_activos.json
python scripts/build_registers_seed.py <mapa.json> apps/registers/data/registros_siempresoft.json
```

Después se vuelve a ejecutar `cargar_datos_siempresoft`. También se puede importar cada registro desde su pantalla con «Importar».
