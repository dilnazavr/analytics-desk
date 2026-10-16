#!/bin/sh
set -e

echo "Waiting for database..."
sleep 2

export FLASK_APP=run.py

echo "Running migrations..."
flask db upgrade || echo "Migration warning (may already be applied)"

echo "Seeding data (roles/users if missing)..."
flask seed || true

PORT="${PORT:-5000}"
echo "Starting gunicorn on 0.0.0.0:${PORT}..."
exec gunicorn --bind "0.0.0.0:${PORT}" --workers 2 --timeout 300 run:app