# Carga total de SiempreSoft (v20)

## Un solo comando

```
docker compose exec web python manage.py cargar_todo_siempresoft
```

El comando carga y enlaza todo lo real que llegó del repositorio de OneDrive. Cada paso va en su propia transacción: si alguno falla, se deshace solo ese paso y los demás siguen. Se puede ejecutar varias veces sin duplicar nada. Para repetir un solo paso: `--paso organigrama` (se puede repetir la opción).

| Paso | Qué hace | Con qué datos |
|---|---|---|
| `datos` | Registros del SGSI y activos con su historial | 1.932 filas de 29 registros; 372 equipos, salidas, revisiones, software y bajas |
| `unificar` | Si un colaborador ya estaba registrado (mismo correo, o mismo nombre y apellido), se usa **su** usuario y **su código**. Los equipos y movimientos pasan a él y el duplicado se elimina | Usuarios del sistema |
| `organigrama` | Ubica a cada colaborador vigente en su puesto según su cargo más reciente | Actas de reunión 2025-2026, revisiones periódicas, salidas de activos, BYOD, Microsoft 365 |
| `documentos` | Registra cada documento que pide el Manual con su archivo real y su versión; deja de decir «falta» | 45 documentos (incluye 26 perfiles de puesto) |
| `contexto` | Carga las páginas 4.1 y 4.2 (Misión y Visión, Organigrama V21, Requisitos legales V0.15, Partes interesadas V0.4) | Copia los archivos a `/app/imports` si no existen y ejecuta `seed_context41` y `seed_context42` |
| `riesgos` | Matriz de riesgos 2026 y modelo de Karim, responsabilidades documentales y autorizaciones de acceso | Importador existente; no repite un archivo ya importado |
| `incidentes` | 93 incidentes RISI (2019-2026) con severidad, estado, responsable y control afectado | Registro de incidentes |
| `auditorias` | 35 auditorías con sus 208 hallazgos y la acción de cada uno | Registro centralizado de medidas correctivas (origen «Auditoría …») |
| `vulnerabilidades` | Software con debilidades conocidas del último inventario de Defender de cada equipo, en estado «por verificar» | Inventarios de software |

## Reglas para no dañar ni duplicar

- **El código del colaborador manda.** Nunca se cambia el `business_code` de un usuario existente. Los usuarios nuevos (`COL-…`) solo se crean si la persona no existe, y se crean sin acceso al sistema.
- **Organigrama:**
  - No se toca a quien ya tiene puesto.
  - Se respeta el cupo de cada puesto.
  - No se ubica a retirados ni a personas cuyo último cargo es anterior a 2025 (salvo que figuren en el inventario 2026).
  - Si el cargo no coincide con un puesto del organigrama, **no se adivina**: se lista como pendiente.
- **Documentos:** si el documento ya tiene ese archivo o esa versión, no se vuelve a subir.
- **4.1 y 4.2:** si ya hay un archivo con el mismo nombre en `/app/imports`, se respeta.

## Resultado esperado del organigrama (con los puestos por defecto)

Se ubican **15** colaboradores. Quedan como pendientes, porque su cargo no existe con ese nombre en el organigrama:

| Colaborador | Cargo según las fuentes |
|---|---|
| Elizabeth Cruz | Responsable de control de calidad |
| Marcelo Vassallo | Jefe de I+D |
| María Piedra | Analista de soporte al cliente |
| Stephanie Fernández | Analista de soporte al cliente |
| Nicol Solano | Responsable de Consultoría |
| Sheyla Quevedo | Jefe de soporte al cliente |
| William Barrantes | Jefe de soporte al cliente |
| Jannyna Pancca | Jefe de Help Desk (puesto ya ocupado por Danae Vilela en 2026) |

## Documentos que el Manual pide y que no llegaron

| Numeral | Documento | Motivo |
|---|---|---|
| 3.1, 7.3 | Política para el uso y gestión de la Inteligencia Artificial | No está en ningún archivo enviado (es nueva en el Manual v0.7) |
| 7.1 | Presupuesto anual | No está en ningún archivo enviado |
| 9.3 | Informe de revisión por parte de la Dirección | La carpeta no se descargó de OneDrive |
| 9.3 | Minutas de reunión (revisión por la Dirección) | La carpeta no se descargó de OneDrive; las actas de reunión sí están en Registros del SGSI |

Estos siguen marcando «falta» porque de verdad no se tienen. Se suben desde el numeral con «Registrar y subir».

## Datos que no se versionan en Git

Agregar al `.gitignore`: tienen nombres, correos e historial de colaboradores, y documentos de uso interno o restringido.

```
apps/assets/data/*.json
apps/registers/data/*.json
apps/dashboard/data/
apps/traceability/data/
```
