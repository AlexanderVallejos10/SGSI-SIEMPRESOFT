# Mantenimiento del proyecto

## Cambios de código

Trabajar en una rama, revisar el diff y ejecutar las verificaciones antes de integrar.
Modificar directamente el módulo correspondiente. No crear scripts que reescriban
código fuente mediante sustituciones de texto o cadenas base64.
Git conserva las versiones anteriores: no incorporar copias `before`, `.bak` o `.backup`.

## Cambios de datos

Conservar las migraciones existentes. Para cambios en modelos, generar y revisar una
nueva migración. Para cargas recurrentes, usar comandos de Django con validación,
transacciones e idempotencia cuando corresponda. No asumir que todos los comandos
actuales ofrecen simulación: revisar su ayuda y su implementación.

## Arranque y datos empresariales

`scripts/entrypoint.sh` aplica migraciones según RUN_MIGRATIONS y ejecuta el proceso
principal. Es un script operativo y se conserva.
Los importadores necesitan sus archivos fuente: varios comandos esperan `/app/imports/`
dentro del contenedor. Restaurar esas fuentes desde la documentación empresarial o
el respaldo original; no volver a ejecutar instaladores históricos para recuperarlas.
Respaldar PostgreSQL y el volumen de media antes de cambios que afecten datos.
No ejecutar `docker compose down -v` como parte de una actualización ordinaria.

## Aplicar esta limpieza al repositorio original

El parche entregado está basado en el ZIP SGSI-SIEMPRESOFT-main recibido para la revisión.
Desde el repositorio local, guardar primero los cambios propios y crear una rama:

```bat
git status
git switch -c refactor/limpieza-estructura
git apply --check C:\ruta\limpieza-estructura.patch
git apply C:\ruta\limpieza-estructura.patch
git diff --stat
```

Si `--check` falla, no forzar: comparar las diferencias con la copia limpia.
No usar `--reject`, ya que puede dejar una aplicación parcial del parche.
El ZIP limpio es una alternativa para revisión, no un respaldo de base de datos o media.
Copiarlo encima del proyecto no elimina los instaladores: preferir el parche.

Después, con el contenedor en marcha:

```bat
docker compose exec web python manage.py check
docker compose exec web python manage.py makemigrations --check --dry-run
```

Ejecutar las pruebas en el entorno de desarrollo descrito en README y revisar el diff.
Versionar el resultado con un commit que describa la limpieza.
Esta entrega no modifica automáticamente el repositorio de GitHub.
