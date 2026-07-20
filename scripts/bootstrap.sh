#!/usr/bin/env bash
# Set up a local dev environment for AI Pharmacy OS (Sprint 2 kernel).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"

echo "==> Creating virtualenv (.venv)"
python3 -m venv "$ROOT/.venv"
# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"

echo "==> Installing backend (dev extras)"
pip install --upgrade pip
pip install -e ".[dev]"

if [ ! -f .env ]; then
  echo "==> Creating .env from template"
  cp .env.example .env
fi

echo "==> Starting Postgres + Redis"
docker compose -f "$ROOT/docker-compose.yml" up -d

echo "==> Running migrations"
alembic upgrade head

echo "Done. Activate with: source .venv/bin/activate"
echo "Run the API with:   make serve"
