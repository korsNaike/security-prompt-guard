.PHONY: install test lint format ci dev smoke load-test docker-up docker-down

install:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .

ci: lint
	uv run pytest -q
	uv run python -m compileall app tests alembic scripts

format:
	uv run ruff format .

dev:
	uv run fastapi dev app/main.py

smoke:
	uv run python scripts/smoke_test.py

load-test:
	uv run python scripts/load_test.py

docker-up:
	docker compose up --build

docker-down:
	docker compose down
