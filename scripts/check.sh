#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export DJANGO_DEBUG=1
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test
node --test tests-js/*.test.cjs
