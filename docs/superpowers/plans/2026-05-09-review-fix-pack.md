# Review Fix Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix review findings for Docker startup, OpenAPI branding, and stable public model metadata.

**Architecture:** Keep the existing FastAPI service and model catalog architecture. Align `.env.example` with Docker Compose credentials, add a DB-backed readiness endpoint for container healthchecks, make OpenAPI description product-specific, and make model catalog sync use an explicit configured display model name instead of deriving it from the Python class name.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, Docker Compose, YAML model config, pytest, Ruff.

---

## File Structure

- Modify `.env.example`: set SecurePrompt Guard app name and Docker-compatible DB URL.
- Modify `app/main.py`: product-specific OpenAPI description and DB-backed `/ready`.
- Modify `docker-compose.yml`: API healthcheck calls `/ready`.
- Modify `config/models.yml`: add explicit `model_name: Rule-Based Prompt Guard Baseline`.
- Modify `app/infrastructure/ml/config_loader.py`: parse `model_name`.
- Modify `app/infrastructure/db/repositories/model_catalog_repository.py`: sync configured model name into DB.
- Modify tests for env/compose/readiness route/OpenAPI/model config/model catalog metadata.
- Add commit `SPG-005 fix docker readiness and model metadata`.

### Task 1: Pin Review Findings In Tests

**Files:**
- Modify: `tests/unit/test_docker_compose_artifacts.py`
- Modify: `tests/unit/test_fastapi_app.py`
- Modify: `tests/unit/test_api_routes.py`
- Modify: `tests/unit/test_model_config_loader.py`
- Modify: `tests/integration/test_model_catalog_sync.py`

- [ ] **Step 1: Add assertions for Docker env and readiness healthcheck**

Add tests that assert:

```python
env = Path(".env.example").read_text()
assert "APP_NAME=SecurePrompt Guard" in env
assert "secure_prompt_guard:secure_prompt_guard@postgres:5432/secure_prompt_guard" in env
assert "/ready" in compose["services"]["api"]["healthcheck"]["test"][-1]
```

- [ ] **Step 2: Add assertions for OpenAPI and route registration**

Add tests that assert:

```python
assert "/ready" in route_paths
assert app.description == "SecurePrompt Guard API for prompt injection, jailbreak, harmful prompt, and data exfiltration classification."
assert client.get("/openapi.json").json()["info"]["description"] == app.description
```

- [ ] **Step 3: Add assertions for configured model display name**

Add tests that assert `load_model_definitions()` exposes `model_name == "Rule-Based Prompt Guard Baseline"` and synced catalog items expose the same `model_name`.

- [ ] **Step 4: Run focused tests and confirm failures**

Run:

```bash
uv run pytest tests/unit/test_docker_compose_artifacts.py tests/unit/test_fastapi_app.py tests/unit/test_api_routes.py tests/unit/test_model_config_loader.py tests/integration/test_model_catalog_sync.py -q
```

Expected: failures until implementation updates env, `/ready`, OpenAPI description, and model config parsing.

### Task 2: Implement Docker Env And Readiness Fix

**Files:**
- Modify: `.env.example`
- Modify: `app/main.py`
- Modify: `docker-compose.yml`

- [ ] **Step 1: Update `.env.example`**

Set:

```env
APP_NAME=SecurePrompt Guard
DATABASE_URL=postgresql+asyncpg://secure_prompt_guard:secure_prompt_guard@postgres:5432/secure_prompt_guard
```

- [ ] **Step 2: Add DB readiness endpoint**

In `app/main.py`, import `HTTPException`, `status`, and `text`. Add:

```python
@app.get("/ready", tags=["health"], summary="Service readiness check")
async def ready() -> dict[str, str]:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from exc
    return {"status": "ready", "service": settings.app_name}
```

- [ ] **Step 3: Point Docker healthcheck at `/ready`**

In `docker-compose.yml`, change API healthcheck URL from `/health` to `/ready`.

- [ ] **Step 4: Run focused Docker/readiness tests**

Run:

```bash
uv run pytest tests/unit/test_docker_compose_artifacts.py tests/unit/test_fastapi_app.py -q
```

Expected: pass.

### Task 3: Implement OpenAPI And Model Metadata Fix

**Files:**
- Modify: `app/main.py`
- Modify: `config/models.yml`
- Modify: `app/infrastructure/ml/config_loader.py`
- Modify: `app/infrastructure/db/repositories/model_catalog_repository.py`

- [ ] **Step 1: Set product-specific FastAPI description**

Use:

```python
description=(
    "SecurePrompt Guard API for prompt injection, jailbreak, harmful prompt, "
    "and data exfiltration classification."
)
```

- [ ] **Step 2: Add `model_name` to config and dataclass**

In `config/models.yml`, add:

```yaml
    model_name: Rule-Based Prompt Guard Baseline
```

In `ModelDefinition`, add `model_name: str`, parse it from `payload["model_name"]`, and keep the existing missing-field error path.

- [ ] **Step 3: Use configured model name during catalog sync**

Change `sync_model_catalog_from_definitions()` to pass:

```python
model_name=definition.model_name
```

- [ ] **Step 4: Run focused API/catalog tests**

Run:

```bash
uv run pytest tests/unit/test_api_routes.py tests/unit/test_model_config_loader.py tests/integration/test_model_catalog_sync.py tests/unit/test_models_api_catalog.py -q
```

Expected: pass.

### Task 4: Final Verification And Commit

**Files:**
- Verify all changed files.

- [ ] **Step 1: Run active-surface grep**

Run:

```bash
rg -n -i "TextMood|text_mood|sentiment|urgent|angry|toxic|UniClassify|uniclassify" README.md pyproject.toml config app scripts tests dashboards prometheus docker-compose*.yml Dockerfile Makefile .github .env.example
```

Expected: no matches.

- [ ] **Step 2: Run full test suite**

Run:

```bash
uv run pytest
```

Expected: pass.

- [ ] **Step 3: Run Ruff**

Run:

```bash
uv run ruff check .
```

Expected: pass.

- [ ] **Step 4: Run compileall**

Run:

```bash
uv run python -m compileall app tests alembic scripts
```

Expected: pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add .env.example app/main.py docker-compose.yml config/models.yml app/infrastructure/ml/config_loader.py app/infrastructure/db/repositories/model_catalog_repository.py tests/unit/test_docker_compose_artifacts.py tests/unit/test_fastapi_app.py tests/unit/test_api_routes.py tests/unit/test_model_config_loader.py tests/integration/test_model_catalog_sync.py
git commit -m "SPG-005 fix docker readiness and model metadata"
```

## Self-Review

- Spec coverage: plan maps to P1 Docker/env/readiness, P2 OpenAPI description, and P3 stable model metadata.
- Placeholder scan: no placeholder markers are present.
- Type consistency: `model_name` is consistently a string field on `ModelDefinition`, and the public model name is `Rule-Based Prompt Guard Baseline`.
