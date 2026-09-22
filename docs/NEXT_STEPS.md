# Pendientes de desarrollo

La limpieza estructural está registrada en CLEANUP.md. No resuelve estos pendientes funcionales:

1. Aplicar autorización por documento y cargo a consulta, visualización y descarga.
2. Restringir la asignación de grupos desde formularios genéricos de usuarios.
3. Completar la metodología de riesgos: catálogos, valoración 5x4 y seguimiento residual.
4. Integrar movimientos de activos y accesos en un flujo de actas de entrega.
5. Incorporar historial de asignaciones de propietarios documentales.
6. Revisar divergencias entre dashboard/dashboard_live y context41/context42.
7. Centralizar escrituras de negocio que actualmente omiten servicios existentes.
8. Ampliar pruebas de permisos, importaciones y flujos completos; validar con PostgreSQL.
9. Preparar configuración y procedimiento de despliegue de producción.

Antes de cargar los Excel se deben validar fechas, cargos, identificadores y escalas.
Las migraciones ya existen y están versionadas; no regenerarlas como paso de instalación.
