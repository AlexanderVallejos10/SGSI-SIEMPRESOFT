# Cambio 01: áreas conectadas al organigrama

## Base y alcance

Cambio preparado sobre `SGSI-SIEMPRESOFT-main.zip` adjunto en esta conversación. No se ha conectado con la base de datos de la empresa ni se ha publicado en GitHub. El repositorio remoto no se ha comparado con este ZIP.

Esta entrega se concentra en las áreas. Conserva la estructura visual principal y los enlaces al detalle del trabajador. El rediseño del tamaño del organigrama y las animaciones no forman parte de este cambio.

## Diagnóstico comprobado en el código

- `seed_organization_chart.py` crea puestos y asignaciones, pero no crea `OrganizationalArea` ni asigna `Position.area`. Por ello, ejecutar esa carga puede dejar un organigrama completo y cero áreas.
- Los modelos ya relacionan área → puesto → asignación → trabajador. No es necesario rehacer esa estructura.
- El catálogo de áreas no tenía detalle ni selección de puestos existentes.
- Los textos de área y cargo del usuario se actualizaban al asignar una persona, pero podían quedar desactualizados al renombrar un área, trasladar un puesto o cerrar una asignación. Una asignación adicional también podía sobrescribir el cargo principal.
- La bitácora automática no incluía el módulo `organization`.

Estos hallazgos describen el código recibido; no demuestran los registros que existen actualmente en la instalación.

## Qué cambia

1. **Crear o editar un área y seleccionar sus puestos.** Se ofrecen los puestos sin área y los propios del área editada. Para trasladar un puesto desde otra área se mantiene la pantalla Editar puesto. Desmarcar un puesto lo deja sin área; no elimina el puesto ni cierra sus asignaciones.
2. **Detalle del área.** Muestra puestos, dependencia jerárquica, trabajadores, vacantes, subáreas y accesos al perfil, a la asignación y a la creación de trabajadores.
3. **Conteos consistentes.** Incluyen puestos activos propios y asignaciones sin fecha de cierre. Una persona con varios puestos en la misma área se cuenta una sola vez. Las subáreas se consultan por separado. Una vacante es un puesto sin asignaciones abiertas, no una plaza libre dentro de un puesto con varios ocupantes.
4. **Enlaces desde el organigrama.** El nombre del área abre su detalle y un aviso identifica los puestos todavía sin área.
5. **Sincronización del perfil.** El puesto principal determina los textos de cargo y área. Los cambios de área, puesto y asignación actualizan esos textos, también desde el administrador. Una asignación adicional no sustituye los datos de la principal. Cerrar la principal limpia sus textos y mantiene el historial.
6. **Validaciones.** Se rechazan ciclos de áreas, un área activa bajo una superior inactiva y la desactivación de áreas con puestos o subáreas activos. La configuración no toma puestos que ya se hayan vinculado a otra área durante la edición.
7. **Trazabilidad.** Altas y cambios de áreas, puestos y asignaciones pasan por la bitácora existente. La sustitución de una asignación principal deja registrado el cierre de la anterior. La atribución de usuario utiliza el contexto de petición existente; tareas ejecutadas fuera de una petición pueden registrarse sin usuario.
8. **Errores de asignación.** Una validación fallida muestra el error en el formulario. Si falla la asignación de un usuario recién creado, esa creación se revierte junto con la operación.

## Permisos y compatibilidad

Las consultas requieren iniciar sesión, igual que el organigrama y el perfil existentes. Crear, editar, vincular y asignar conserva el criterio actual: superusuario o permiso `organization.change_position`. No se implementa en este cambio una separación nueva de permisos por cargo o área.

No cambian las declaraciones de campos del modelo ni se añaden migraciones. No se crean áreas de ejemplo ni se deducen áreas a partir del nombre de los cargos. Hasta configurar las áreas reales, el contador puede continuar en cero; ahora la pantalla indica cómo completarlas.

Los campos de texto heredados `User.area` y `User.position` tienen un máximo de 120 caracteres. Las copias de compatibilidad respetan ese límite; el nombre y título completos permanecen en los modelos organizacionales y en su vista de detalle. La relación con el puesto es la fuente de la información organizacional. Las escrituras masivas mediante `QuerySet.update`, `bulk_update` o SQL no ejecutan las señales de sincronización ni las señales de auditoría; el flujo incluido usa `save()`.

No se integran todavía documentos, activos, riesgos ni procesos por área. Se conserva la convención existente de considerar abierta una asignación sin fecha de cierre; la gestión de asignaciones futuras requiere una etapa específica.

## Validación de esta entrega

- Sintaxis Python de los archivos modificados: comprobada mediante análisis AST y compilación.
- Declaraciones de campos de los modelos: comparadas con el original, sin cambios.
- El parche se comprueba sobre una copia del ZIP y se compara el resultado con los archivos preparados.
- Se incluyen **20 pruebas Django** para creación, relaciones, conteos, permisos, sincronización, ciclos, bitácora y reversión de una asignación fallida.
- **Las pruebas Django NO se ejecutaron aquí.** El entorno no tiene Django y el acceso a PyPI responde HTTP 403. No hay resultados de `manage.py check`, migraciones ni pruebas funcionales para esta entrega.
- No se realizó una comprobación visual en navegador ni una prueba en Docker/PostgreSQL.

Debe validarse en una copia de desarrollo antes de usarlo con los datos de la empresa. Las instrucciones de aplicación están en `LEEME.md`, dentro del paquete de entrega.
