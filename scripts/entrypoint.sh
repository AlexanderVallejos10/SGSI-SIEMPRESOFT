#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS:-True}" = "True" ]; then
  echo "Applying database migrations..."
  python manage.py migrate --noinput
fi

if [ "${COLLECT_STATIC:-False}" = "True" ]; then
  echo "Collecting static files..."
  python manage.py collectstatic --noinput
fi

exec "$@"
