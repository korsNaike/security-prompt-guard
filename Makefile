.PHONY: install test lint format ci dev smoke load-test acceptance migrate docker-up docker-down docker-logs

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

migrate:
	uv run alembic upgrade head

smoke:
	uv run python scripts/smoke_test.py

load-test:
	uv run python scripts/load_test.py

acceptance:
	uv run python scripts/acceptance_scenario.py

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f api worker beat
