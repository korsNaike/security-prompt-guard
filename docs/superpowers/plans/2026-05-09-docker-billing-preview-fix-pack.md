# Docker Billing Preview Fix Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the second review pack: one-command Docker startup, close unauthenticated sync-preview bypass, correct promo-code repeat semantics, expose promo expiry in admin API, and make Streamlit token application explicit.

**Architecture:** Keep the paid async classification flow as the only classification API path. Run Alembic before the API process starts in Docker, make readiness verify the migrated schema, remove the public sync-preview endpoint, check duplicate promo activation before global activation limits, thread `valid_until` through admin promo-code create, and use a Streamlit form submit button for JWT token application.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, Alembic, Docker Compose, Pydantic, Streamlit, pytest, Ruff.

---

## File Structure

- Modify `docker-compose.yml`: API command runs `alembic upgrade head` before FastAPI.
- Modify `app/main.py`: `/ready` checks migrated schema, not just DB connectivity.
- Modify `app/api/v1/classifications.py`: remove `sync-preview`.
- Modify `scripts/acceptance_scenario.py`: remove sync-preview call.
- Modify `app/infrastructure/db/repositories/billing_repository.py`: duplicate promo activation check before max activation check; accept `valid_until` in `create_promo_code`.
- Modify `app/api/v1/admin.py` and `app/schemas/admin.py`: accept and return promo `valid_until`.
- Modify `scripts/streamlit_dashboard.py`: token input uses a form submit button and session state.
- Modify tests covering Docker readiness, removed sync-preview, promo repeat conflict, promo expiry API schema, and Streamlit token form.
- Add commit `SPG-006 fix docker migrations billing and preview`.

### Task 1: Pin Review Findings In Tests

**Files:**
- Modify: `tests/unit/test_docker_compose_artifacts.py`
- Modify: `tests/unit/test_api_routes.py`
- Modify: `tests/integration/test_billing_repository.py`
- Modify: `tests/unit/test_admin_api.py`
- Modify: `tests/unit/test_streamlit_dashboard_artifacts.py`

- [ ] **Step 1: Assert Docker API runs migrations and readiness checks schema**

Add assertions:

```python
assert "alembic upgrade head" in compose["services"]["api"]["command"]
assert "python -m fastapi" in compose["services"]["api"]["command"]
```

Add `/ready` tests that monkeypatch `app.main.AsyncSessionLocal`, capture the executed SQL, and assert it references the `users` table.

- [ ] **Step 2: Assert sync-preview is not exposed**

Update route tests:

```python
assert "/api/v1/classifications/sync-preview" not in response.json()["paths"]
assert client.post("/api/v1/classifications/sync-preview", json={...}).status_code == 405
```

- [ ] **Step 3: Assert duplicate promo activation wins over max activation limit**

Add integration test where one user activates a promo with `max_activations=1`, then activates it again and gets `PromoCodeAlreadyActivatedError`, not `PromoCodeInvalidError`.

- [ ] **Step 4: Assert admin promo schema supports expiry**

Add schema-level test:

```python
payload = AdminPromoCodeCreateRequest(
    code="SPRING",
    credits_amount=50,
    max_activations=2,
    valid_until=datetime(2026, 6, 1, tzinfo=UTC),
)
assert payload.valid_until == datetime(2026, 6, 1, tzinfo=UTC)
```

- [ ] **Step 5: Assert Streamlit dashboard has explicit token form submit**

Add artifact test checking `scripts/streamlit_dashboard.py` contains `st.form("api-token-form")` and `st.form_submit_button("Apply token")`.

- [ ] **Step 6: Run focused tests and confirm failures**

Run:

```bash
uv run pytest tests/unit/test_docker_compose_artifacts.py tests/unit/test_api_routes.py tests/integration/test_billing_repository.py tests/unit/test_admin_api.py tests/unit/test_streamlit_dashboard_artifacts.py -q
```

Expected: failures before implementation.

### Task 2: Fix Docker Migration And Readiness

**Files:**
- Modify: `docker-compose.yml`
- Modify: `app/main.py`

- [ ] **Step 1: Run Alembic before API startup**

Set API command to:

```yaml
command: >-
  sh -c "uv run alembic upgrade head &&
  uv run python -m fastapi run app/main.py --host 0.0.0.0 --port 8000"
```

- [ ] **Step 2: Make `/ready` validate migrated schema**

Change readiness query to:

```python
await session.execute(text("SELECT 1 FROM users LIMIT 1"))
```

An empty table is fine; a missing table fails readiness.

- [ ] **Step 3: Run focused Docker/readiness tests**

Run:

```bash
uv run pytest tests/unit/test_docker_compose_artifacts.py tests/unit/test_api_routes.py -q
```

Expected: pass.

### Task 3: Remove Sync Preview Bypass

**Files:**
- Modify: `app/api/v1/classifications.py`
- Modify: `scripts/acceptance_scenario.py`
- Modify: `tests/unit/test_api_routes.py`

- [ ] **Step 1: Delete sync-preview route**

Remove `@router.post("/sync-preview")`, its function, and unused imports `ClassificationInput` and `new_request_id`.

- [ ] **Step 2: Remove acceptance preview call**

Delete the `preview = request_json(... "/api/v1/classifications/sync-preview" ...)` block and its assertion. The acceptance scenario should go directly from balance check to paid async classification.

- [ ] **Step 3: Run focused route and acceptance tests**

Run:

```bash
uv run pytest tests/unit/test_api_routes.py tests/unit/test_acceptance_scenario.py -q
```

Expected: pass.

### Task 4: Fix Promo-Code Semantics And Expiry API

**Files:**
- Modify: `app/infrastructure/db/repositories/billing_repository.py`
- Modify: `app/schemas/admin.py`
- Modify: `app/api/v1/admin.py`
- Modify: `tests/integration/test_billing_repository.py`
- Modify: `tests/unit/test_admin_api.py`

- [ ] **Step 1: Check existing activation before max activation limit**

Move `_get_promo_activation()` before max activation check in `activate_promo_code()`.

- [ ] **Step 2: Thread valid_until through repository and admin API**

Change repository signature:

```python
async def create_promo_code(
    self,
    *,
    code: str,
    credits_amount: int,
    max_activations: int | None,
    valid_until: datetime | None = None,
) -> PromoCodeModel:
```

Pass `valid_until=valid_until` into `PromoCodeModel`.

In `AdminPromoCodeCreateRequest`, add:

```python
valid_until: datetime | None = None
```

In `AdminPromoCodeResponse`, add:

```python
valid_until: datetime | None = None
```

In `create_promo_code()`, pass and return `valid_until`.

- [ ] **Step 3: Run focused billing/admin tests**

Run:

```bash
uv run pytest tests/integration/test_billing_repository.py tests/unit/test_admin_api.py tests/unit/test_billing_api.py -q
```

Expected: pass.

### Task 5: Fix Streamlit Token Apply UX

**Files:**
- Modify: `scripts/streamlit_dashboard.py`
- Modify: `tests/unit/test_streamlit_dashboard_artifacts.py`

- [ ] **Step 1: Use a token form and session state**

Replace direct `st.text_input("API token", type="password")` with:

```python
with st.form("api-token-form"):
    token_input = st.text_input("API token", type="password", value=st.session_state.get("api_token", ""))
    token_submitted = st.form_submit_button("Apply token")
if token_submitted:
    st.session_state["api_token"] = token_input.strip()
token = st.session_state.get("api_token", "")
```

- [ ] **Step 2: Run Streamlit artifact test**

Run:

```bash
uv run pytest tests/unit/test_streamlit_dashboard_artifacts.py -q
```

Expected: pass.

### Task 6: Final Verification And Commit

**Files:**
- Verify all changed files.

- [ ] **Step 1: Run active-surface grep**

Run:

```bash
rg -n -i "TextMood|text_mood|sentiment|urgent|angry|toxic|UniClassify|uniclassify" README.md pyproject.toml config app scripts tests dashboards prometheus docker-compose*.yml Dockerfile Makefile .github .env.example
```

Expected: no matches.

- [ ] **Step 2: Run full tests**

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
git add docker-compose.yml app/main.py app/api/v1/classifications.py scripts/acceptance_scenario.py app/infrastructure/db/repositories/billing_repository.py app/schemas/admin.py app/api/v1/admin.py scripts/streamlit_dashboard.py tests/unit/test_docker_compose_artifacts.py tests/unit/test_api_routes.py tests/integration/test_billing_repository.py tests/unit/test_admin_api.py tests/unit/test_streamlit_dashboard_artifacts.py docs/superpowers/plans/2026-05-09-docker-billing-preview-fix-pack.md
git commit -m "SPG-006 fix docker migrations billing and preview"
```

## Self-Review

- Spec coverage: plan maps to P0 Docker/migrations/readiness, P1 sync-preview, P1 promo repeat conflict, P2 promo expiry API, and P2 Streamlit token application.
- Placeholder scan: no placeholder markers are present.
- Type consistency: `valid_until` remains `datetime | None`; paid classification remains the only route that executes model inference through API.
