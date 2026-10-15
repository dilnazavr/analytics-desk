#!/bin/sh
set -e

echo "Waiting for database..."
sleep 3

echo "Running migrations..."
flask db upgrade || {
  echo "Migration failed, trying to create tables via seed path..."
}

echo "Seeding data..."
flask seed || true

echo "Starting gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 300 --reload run:app
