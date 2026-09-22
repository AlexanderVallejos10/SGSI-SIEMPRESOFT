.PHONY: up down build logs shell migrations migrate superuser test lint

up:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f web

shell:
	docker compose exec web python manage.py shell

migrations:
	docker compose run --rm web python manage.py makemigrations

migrate:
	docker compose run --rm web python manage.py migrate

superuser:
	docker compose run --rm web python manage.py createsuperuser

test:
	docker compose run --rm web pytest

lint:
	docker compose run --rm web ruff check .
