#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export DJANGO_DEBUG=1 POLISKILLED_DEMO=1
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py import_catalog --archive-demo
exec .venv/bin/python manage.py runserver 127.0.0.1:8000 --noreload
