# AI Pharmacy OS — developer shortcuts.
.PHONY: help install lint typecheck contracts test check up down migrate serve

help:
	@echo "install    - install backend with dev extras into current venv"
	@echo "lint       - ruff check + format check"
	@echo "typecheck  - mypy"
	@echo "contracts  - import-linter dependency rules"
	@echo "test       - pytest"
	@echo "check      - lint + contracts + typecheck + test"
	@echo "up/down    - start/stop postgres+redis (docker compose)"
	@echo "migrate    - alembic upgrade head"
	@echo "serve      - run FastAPI dev server"

install:
	cd backend && pip install -e ".[dev]"

lint:
	cd backend && ruff check . && ruff format --check .

typecheck:
	cd backend && mypy

contracts:
	cd backend && lint-imports

test:
	cd backend && pytest

check: lint contracts typecheck test

up:
	docker compose up -d

down:
	docker compose down

migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python -m seeds.run

serve:
	cd backend && uvicorn pharmacy_os.main:app --reload
