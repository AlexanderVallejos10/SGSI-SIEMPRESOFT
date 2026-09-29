# SGSI SIEMPRESOFT

Aplicación Django para la gestión documental y operativa del SGSI de SiempreSoft.
El proyecto está en desarrollo: disponer de un módulo no garantiza que su flujo de negocio esté completo.

## Tecnología y estructura

Python 3.12, Django 5.2, Django ORM, PostgreSQL 16 y Docker Compose.
La aplicación sigue MTV y utiliza servicios y selectores en parte de sus módulos.

| Ruta | Responsabilidad |
| --- | --- |
| `apps/` | Módulos de negocio, modelos, vistas, servicios, comandos y pruebas |
| `config/` | Configuración por entorno, rutas globales, WSGI y ASGI |
| `templates/` | Plantillas HTML de Django |
| `static/` | CSS y JavaScript mantenidos como código fuente |
| `requirements/` | Dependencias de aplicación y desarrollo |
| `scripts/` | Arranque del contenedor |
| `docs/` | Arquitectura, mantenimiento, pendientes y registro de limpieza |
| `manage.py` | Entrada a los comandos de Django |

## Primer arranque en Windows con Docker

Desde la carpeta del proyecto, en CMD:

```bat
copy .env.example .env
```

Editar `.env`: definir una clave secreta propia y credenciales coherentes en
`POSTGRES_PASSWORD` y `DATABASE_URL`. No versionar este archivo.

```bat
docker compose up --build -d
docker compose exec web python manage.py check
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py seed_organization_chart --apply
docker compose exec web python manage.py configure_sgsi_structure --apply --map
```

El script de arranque ejecuta las migraciones existentes cuando `RUN_MIGRATIONS=True`.
No se necesita ejecutar instaladores históricos ni generar migraciones para una instalación normal.

- Aplicación: http://localhost:8000/
- Administración: http://localhost:8000/admin/
- Estado del servicio: http://localhost:8000/health/

Este Compose utiliza `runserver` y la configuración de desarrollo del ejemplo.
No es una configuración lista para producción.

## Desarrollo y verificación

En un entorno virtual con Python 3.12, instalar `requirements/dev.txt`.
Configurar las variables de entorno y una base de datos de prueba antes de ejecutar:

```text
python manage.py check
python manage.py makemigrations --check --dry-run
pytest -q
```

`makemigrations` sin `--check` corresponde al desarrollo de cambios en modelos;
las migraciones resultantes se revisan y se versionan.
La imagen Docker actual instala solo `requirements/base.txt`: pytest y ruff requieren
las dependencias de desarrollo; no están disponibles en esa imagen por defecto.

## Datos iniciales y documentos

Una base nueva no contiene los documentos ni los registros del entorno de trabajo.
Los comandos de carga están en `apps/<modulo>/management/commands/`.
Consultar `python manage.py help <comando>` y revisar su alcance antes de ejecutarlos.
Algunos comandos cargan datos históricos específicos de SiempreSoft.

Los archivos empresariales se proporcionan por separado en `imports/` o mediante
las pantallas de carga. Los archivos subidos se almacenan en `media/`.
Las dos carpetas están excluidas del repositorio; no sustituirlas al actualizar código.
Los antiguos instaladores incluían algunos documentos incrustados: esta copia limpia
no los distribuye dentro del código. Consultar `docs/CLEANUP.md` para su procedencia.

La pantalla **Trazabilidad > Importar fuentes** recibe la matriz de riesgos, la
lista de propietarios y la lista de autorizaciones. Primero muestra una simulación;
la carga solo se confirma con **Aplicar importación**. Las coincidencias ambiguas
quedan pendientes para revisión y no conceden acceso automáticamente.

Las áreas son unidades organizativas. Los procesos se vinculan a un área
responsable y pueden involucrar otras áreas, cargos y personas. No se crean áreas
a partir del nombre de un proceso. Las actas de asignación y devolución se generan
desde la ficha del usuario y conservan una copia inmutable al emitirse.

## Documentación

- [Arquitectura](docs/ARCHITECTURE.md)
- [Mantenimiento](docs/MAINTENANCE.md)
- [Registro de limpieza](docs/CLEANUP.md)
- [Trabajo pendiente](docs/NEXT_STEPS.md)
