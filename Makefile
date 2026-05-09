.PHONY: install test lint format dev docker-up docker-down

install:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

dev:
	uv run fastapi dev app/main.py

docker-up:
	docker compose up --build

docker-down:
	docker compose down
