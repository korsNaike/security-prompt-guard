from pathlib import Path

import yaml


def test_compose_uses_configurable_host_ports() -> None:
    compose = yaml.safe_load(Path("docker-compose.yml").read_text())

    assert compose["services"]["postgres"]["ports"] == ["${POSTGRES_PORT:-5433}:5432"]
    assert compose["services"]["redis"]["ports"] == ["${REDIS_PORT:-6380}:6379"]
    assert compose["services"]["api"]["ports"] == ["${API_PORT:-8000}:8000"]


def test_runtime_commands_use_python_modules() -> None:
    compose = yaml.safe_load(Path("docker-compose.yml").read_text())

    assert "python -m fastapi" in compose["services"]["api"]["command"]
    assert "python -m celery" in compose["services"]["worker"]["command"]
    assert "python -m celery" in compose["services"]["beat"]["command"]
    assert "--pool=solo" in compose["services"]["worker"]["command"]


def test_services_have_healthchecks_and_healthy_dependencies() -> None:
    compose = yaml.safe_load(Path("docker-compose.yml").read_text())

    assert "healthcheck" in compose["services"]["postgres"]
    assert "healthcheck" in compose["services"]["redis"]
    assert "healthcheck" in compose["services"]["api"]
    assert compose["services"]["api"]["depends_on"]["postgres"]["condition"] == "service_healthy"
    assert compose["services"]["worker"]["depends_on"]["api"]["condition"] == "service_healthy"


def test_override_preserves_container_virtualenv() -> None:
    override = yaml.safe_load(Path("docker-compose.override.yml").read_text())

    assert "api_venv:/app/.venv" in override["services"]["api"]["volumes"]
    assert "worker_venv:/app/.venv" in override["services"]["worker"]["volumes"]


def test_dockerignore_excludes_local_virtualenv() -> None:
    content = Path(".dockerignore").read_text().splitlines()

    assert ".venv" in content
    assert ".git" in content
