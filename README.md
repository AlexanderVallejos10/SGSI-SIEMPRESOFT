# SGSI SIEMPRESOFT - Django

Base técnica inicial para convertir la gestión documental y operativa del SGSI en un sistema integrado.

## Stack
- Python 3.12
- Django 5.2 LTS
- Django MTV
- Django ORM
- PostgreSQL 16
- Docker / Docker Compose
- Gunicorn para producción
- WhiteNoise para estáticos
- `.env` para configuración

## Primer arranque

```bash
docker compose build
docker compose run --rm web python manage.py makemigrations
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py createsuperuser
docker compose up
```

Abrir:
- SGSI: http://localhost:8000/
- Administración: http://localhost:8000/admin/
- Health check: http://localhost:8000/health/

## Por qué PostgreSQL
El SGSI requiere integridad referencial, muchas relaciones, historial, JSON técnico para bitácora, consultas complejas e índices. PostgreSQL se integra nativamente con Django ORM y es adecuado para el crecimiento esperado.

## Clean Code aplicado
La estructura evita colocar reglas del negocio en vistas o templates. Las consultas complejas van a `selectors.py`; las operaciones que modifican estado y requieren transacciones van a `services.py`; el ORM mantiene el modelo relacional.

## Importante
Este paquete es la **base técnica v0.1**, no la implementación final de los diez mockups. Ya contiene los dominios centrales y un dashboard inicial conectado al ORM. Las migraciones se generan en el primer arranque para quedar versionadas en el repositorio desde el inicio.
