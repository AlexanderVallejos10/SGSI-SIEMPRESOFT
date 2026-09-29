# Arquitectura del SGSI

## Organización actual

Aplicación modular Django con patrón MTV y persistencia mediante el ORM.
`config/urls.py` conecta las rutas; las vistas coordinan solicitudes y respuestas;
los modelos representan datos y relaciones; las plantillas presentan el contenido.

| Módulo | Responsabilidad |
| --- | --- |
| core | Modelos comunes, estados y protección de eliminación |
| accounts | Usuarios, roles y registros de accesos corporativos |
| auditlog | Registro de eventos de los módulos conectados a sus señales |
| documents | Documentos, versiones, evidencias e inventario de fuentes |
| controls | Controles, requisitos y vínculos documentales |
| assets | Activos, movimientos y mantenimiento |
| risks | Riesgos, evaluaciones y tratamientos |
| incidents | Incidentes y vulnerabilidades |
| assurance | Auditorías, hallazgos y mejoras |
| organization | Áreas, cargos y asignaciones |
| processes | Mapa de procesos y relaciones con otros módulos |
| context41 | Documentos del contexto 4.1 y requisitos legales |
| context42 | Partes interesadas y registros del contexto 4.2 |
| dashboard | Consultas, reportes y gestión genérica de entidades |
| dashboard_live | Tablero principal y datos importados de su Excel |
| traceability | Importación controlada, permisos documentales, matriz de riesgos y actas |

## Convenciones de mantenimiento

- `models.py`: entidades, relaciones y restricciones persistentes.
- `forms.py`: validación de datos recibidos por formularios.
- `services.py`: operaciones de negocio y transacciones cuando corresponda.
- `selectors.py`: consultas de lectura reutilizables.
- `views.py`: coordinación HTTP y control de acceso.
- `management/commands/`: operaciones explícitas de carga o mantenimiento.
- `migrations/`: evolución versionada del esquema; se conserva su historial.

Estas responsabilidades son la dirección de mantenimiento. Su aplicación actual
es parcial: existen operaciones directas en vistas y en la gestión genérica.
No se presenta esta estructura como una implementación completa de Clean Architecture.

## Identidad e historial

Los UUID identifican internamente las entidades. Los códigos de negocio no los sustituyen.
Se utilizan estados, versiones y eventos para conservar trazabilidad.
La cobertura de auditoría y protección de eliminación debe verificarse por módulo;
no es uniforme en toda la aplicación.

## Dependencias que se conservan

`dashboard` y `dashboard_live` siguen activos y almacenan conjuntos de datos distintos.
Su consolidación requiere revisar consultas, datos y migraciones: no basta con eliminar
uno de los directorios. Lo mismo aplica a los requisitos legales de context41 y context42.

Los nombres versionados de algunos CSS y JS siguen referenciados por las plantillas.
Son archivos activos, no instaladores; se conservan hasta una refactorización coordinada.

## Relaciones operativas

- Un área agrupa cargos; una asignación vincula temporalmente una persona con un cargo.
- Un proceso tiene un área responsable y puede vincular áreas, cargos y participantes adicionales.
- Los riesgos se vinculan a uno o varios procesos sin perder el texto de la fuente original.
- La propiedad y la autorización documental conservan persona, cargo, fecha y fila de origen.
- Una autorización importada no entra en vigor hasta que un gestor la verifica.
- Las actas de ingreso y salida reúnen equipos y accesos y congelan sus datos al emitirse.
