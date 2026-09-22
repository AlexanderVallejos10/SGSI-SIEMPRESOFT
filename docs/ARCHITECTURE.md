# Arquitectura base del SGSI

## Decisiones cerradas
- Framework: Django 5.2 LTS.
- Patrón web: MTV de Django.
- Persistencia: Django ORM.
- Base de datos: PostgreSQL 16.
- Entorno: Docker / Docker Compose.
- Configuración: variables de entorno `.env`.
- Código: modular por dominio, evitando lógica de negocio en vistas/templates.

## Capas pragmáticas dentro de cada app
- `models.py`: estado persistente y relaciones ORM.
- `selectors.py`: consultas de lectura optimizadas.
- `services.py`: casos de uso y reglas transaccionales de escritura.
- `forms.py`: validación HTTP/MTV cuando corresponda.
- `views.py`: coordinación de request/response, sin reglas de negocio.
- `templates/`: presentación.
- `admin.py`: administración operativa inicial y soporte de carga controlada.

## Módulos iniciales
- accounts: usuarios e identidad SGSI.
- auditlog: bitácora técnica inmutable para usuarios funcionales.
- documents: documentos, versiones y evidencias.
- controls: marcos y controles (ISO 27001:2022, SUNAT u otros).
- assets: activos, movimientos y mantenimiento.
- risks: riesgo, evaluaciones y tratamientos.
- incidents: incidentes, cronología y vulnerabilidades.
- assurance: auditorías, hallazgos y acciones de mejora.
- dashboard: vista consolidada calculada desde datos reales.

## Regla de identificación
Los UUID son claves internas. Códigos como `USR-001`, `EQ-002`, `R-007`, `INC-0021` o `8.8` son identificadores de negocio y nunca reemplazan la clave interna.

## Historial
No se diseña eliminación física como mecanismo ordinario de edición de información auditable. La evolución se resuelve mediante estados, eventos y versionado.
