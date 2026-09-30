# Repositorio de documentos online de SiempreSoft: análisis por área

Carpetas recibidas: 01, 03, 04, 05, 06 y 07. Faltan **02 - Área de Seguridad de la Información** y **11 - SGSST**, que llegarán después. Las carpetas «Capacitación Marytha», «PTS para Demo - Consultoría» y «Versiones de App Móvil» no se enviaron. Por su nombre, no son documentos del SGSI.

## Resumen

| Carpeta | Archivos | Qué trae | Qué aporta |
|---|---|---|---|
| 01 - Siempresoft | 128 | Idéntico al envío anterior | Nada nuevo |
| 03 - Consultoría | 8 | Procedimiento de implantación V0.7, flujo del extractor | 2 documentos vigentes |
| 04 - Soporte al cliente | 34 | 3 procedimientos vigentes, formato de reporte de incidencia, base de conocimiento, tarjetas Trello | Documentos de operación (8.x) |
| 05 - Desarrollo | 70 | Análisis y programación: política de desarrollo seguro, estándares, cambios críticos, ciclo de vida | Controles 8.25-8.32; **registro nuevo de librerías** |
| 06 - Producción | 304 | QA, despliegue, infraestructura, OSE y API PSE | Controles 8.x y 5.30; **registro nuevo de usuarios**; OSE 2023; **224 archivos con secretos** |
| 07 - Administración | 209 | RR. HH. (26 perfiles de puesto, organigrama V21, procedimientos, formatos) y Logística (proveedores, áreas seguras, inventario de PC) | Controles 6.x, 5.19-5.22 y 7.x; perfiles para el organigrama |

## Nuevo en el sistema (v16)

| Registro | Origen | Anexo A |
|---|---|---|
| Inventario de librerías externas autorizadas (35 librerías, 14 proveedores) | 05 / 02 - Programación / Registro | 8.28 |
| Registro de creación de usuarios | 06 / 03 - Infraestructura / Registros | 5.16, 5.18 |
| Requisitos y obligaciones del OSE **2023** | 06 / 04 - Siempresoft OSE / Registros | Se importa como año 2023 del registro que ya existe |

## Documentos vigentes y su control del Anexo A

Se cargan con la cadena de fuentes (`import_source_inventory` y siguientes). Su nombre dice «vigente», así que el clasificador los marca solos.

**Desarrollo (05)**
- Política de desarrollo seguro V0.9: 8.25.
- Estándares de desarrollo V0.10 y Estándares mínimos de seguridad V0.9: 8.28.
- Manual del ciclo de vida del software V0.3: 8.25.
- Procedimiento de análisis de requerimientos V0.11: 8.26.
- Procedimiento de programación de requerimientos V0.7: 8.28.
- Procedimiento para cambios críticos V0.10 y formato de acta de cambio crítico: 8.32.
- Instructivos de Azure Boards v0.4 y Team Explorer v0.6: 8.4.

**Producción (06)**
- Procedimiento de pruebas de control de calidad V0.5 y checklists de QA y de seguridad: 8.29.
- Replicación de errores V0.2: 8.31.
- Despliegue de nueva versión V0.6, reversión de instalación V0.3 y checklist de despliegue: 8.32.
- Reinicio de máquinas virtuales en Azure V0.3: 8.6.
- Política de transferencia de información V0.6: 5.14.
- Instructivo del plan de recuperación ante desastre y acta de activación del plan: 5.30.
- Backup y restauración de bases de datos: 8.13.
- Monitoreo de performance SQL Server: 8.6.
- Buenas prácticas de seguridad en Windows Server: 8.9.
- Cambio de apikey y otorgar acceso por base de datos: 5.17 y 5.18.
- Diagrama del ciclo de vida de los comprobantes y arquitecturas OSE y API PSE: 5.9 y 8.27.

**Soporte (04)**
- Procedimiento de atención al cliente V0.6, de envío de comprobantes V0.7 y de validación de comprobantes V0.3: procesos del alcance (4.3).
- Formato de reporte de incidencia: 6.8.

**Consultoría (03)**
- Procedimiento de implantación V0.7: proceso del alcance (4.3). El retiro de accesos del consultor corresponde a 5.18.

**Recursos Humanos (07/01)**
- Procedimiento de selección, capacitación, inducción y evaluación V0.10: 6.1 y 6.3.
- Terminación o cambio de puesto V0.4: 6.5.
- Reglamento interno de trabajo V0.3: 6.4.
- Compromiso de no divulgación: 6.6.
- Código de conducta: 5.4.
- Autoevaluación para el teletrabajo: 6.7.
- Actas de asignación y devolución de accesos al área de producción y de materiales: 5.11 y 5.18.
- Declaración jurada de salida de activos: 7.10.
- Declaración de aceptación de documentos del SGSI: 5.1.
- **26 perfiles de puesto** y **Organigrama V21**: van en Organización. Cada puesto del organigrama recibe su perfil en PDF, que es lo que pide el Manual en 7.2.

**Logística (07/02)**
- Política de seguridad para proveedores V0.8: 5.19.
- Cláusulas de seguridad para proveedores V0.5 y declaración de confidencialidad del proveedor: 5.20.
- Control de monitoreo de servicios de proveedores: 5.22.
- Planos por nivel y restricciones de áreas seguras: 7.1, 7.2 y 7.6.
- Acta de visita: 7.2.
- **Inventario de escritorios y PC (2023-2026):** va en «Activos y equipos». No se crea como registro, para no duplicarlo.

## No se usa

- **Tarjetas Trello de 2019** (Soporte): seguimiento operativo antiguo, no es registro del SGSI.
- **Grabaciones .mp4 de llamadas** (Producción): no son documentos.
- **Scripts .sql, .ps1 y .exe**: herramientas de trabajo, no documentos.
- **Leyes laborales de RR. HH.**: corresponden al SGSST (carpeta 11). Se revisan cuando llegue.
- **Formatos vacíos de RR. HH.** (vacaciones, permisos, lista de colaboradores): plantillas con espacio para datos personales. No se cargan datos.

## Secretos: omitidos por el sistema

En `06 - Área de Producción/03 - Infraestructura Tecnológica` hay **224 archivos**:
- 37 certificados S/MIME con llave privada (`.p12`);
- certificados VPN por colaborador (2019-2024);
- claves de recuperación de **BitLocker** por equipo;
- el certificado SSL comodín de siempresoft.com;
- el certificado de la CA interna.

Desde v16, `import_source_inventory` los **omite sin leerlos ni guardarlos** y los lista al final como «OMITIDOS POR SEGURIDAD». Lo mismo pasa con las claves SSH que venían en la carpeta 02.

Recomendación, a decidir con Karim:
1. Mover estos archivos a un almacén de secretos (por ejemplo, Azure Key Vault) y retirarlos de SharePoint.
2. Revisar las claves de BitLocker: aunque la carpeta diga «NO VIGENTE», siguen sirviendo si el equipo o el disco sigue en uso.
3. Revocar los certificados de personas que ya no trabajan en la empresa.

## Pendiente para cuando lleguen 02 y 11

- **02:** registros de incidentes (RISI), medidas correctivas, minutas de revisión por la dirección, auditorías y registros 02 a 18. Varios encajan en «Registros del SGSI», con el mismo motor.
- **11 - SGSST:** es otro sistema de gestión (ISO 45001 / Ley 29783). Hay que decidir si entra en esta plataforma o solo se enlaza.
- **Carpeta pesada:** conviene subirla por partes (una subcarpeta por ZIP). El importador acepta hasta 2 GB descomprimidos por ZIP.
