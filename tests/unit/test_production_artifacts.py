from pathlib import Path

import yaml


def test_ci_runs_lint_tests_and_compileall() -> None:
    content = Path(".github/workflows/ci.yml").read_text()

    assert "uv run ruff check ." in content
    assert "uv run pytest -q" in content
    assert "compileall app tests alembic scripts" in content


def test_makefile_has_hardening_targets() -> None:
    content = Path("Makefile").read_text()

    assert "ci:" in content
    assert "smoke:" in content
    assert "load-test:" in content


def test_test_compose_defines_postgres_and_redis() -> None:
    compose = yaml.safe_load(Path("docker-compose.test.yml").read_text())

    assert "postgres-test" in compose["services"]
    assert "redis-test" in compose["services"]


def test_runbook_and_security_review_exist() -> None:
    runbook = Path("docs/deployment/runbook.md").read_text()
    security = Path("docs/security/security_review.md").read_text()

    assert "Rollback" in runbook
    assert "Model Supply Chain" in security


def test_smoke_and_load_scripts_are_environment_configurable() -> None:
    smoke = Path("scripts/smoke_test.py").read_text()
    load = Path("scripts/load_test.py").read_text()

    assert "UNICLASSIFY_BASE_URL" in smoke
    assert "LOAD_TEST_REQUESTS" in load
    assert "LOAD_TEST_CONCURRENCY" in load
