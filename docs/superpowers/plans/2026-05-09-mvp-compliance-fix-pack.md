# MVP Compliance Fix Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining MVP acceptance gaps from the latest full test run: Streamlit, analytics, loyalty discounts, coverage gate, cache-hit billing, version-aware cache keys, input limits, batch item costs, persisted metrics, and unknown-model `404`.

**Architecture:** Keep the existing FastAPI/Celery/SQLAlchemy architecture. Add missing behavior through focused repository/service/API extensions, with DB-derived reporting for analytics and metrics. Preserve the model registry and catalog design; do not add external model downloads or change the queue system.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy async, Alembic, Celery, Docker Compose, Streamlit, pytest, pytest-cov, Ruff.

---

## File Structure

- Modify `pyproject.toml`: add `streamlit` runtime dependency and `pytest-cov` dev dependency.
- Modify `docker-compose.yml`: add required `streamlit` service and port.
- Create `scripts/streamlit_dashboard.py`: minimal API-backed dashboard.
- Modify `app/schemas/classifications.py`: enforce `text <= 5000`, `items <= 100`.
- Modify `app/application/classifications/use_cases.py`: apply loyalty-discounted cost and batch limit 100.
- Modify `app/api/v1/classifications.py`: map `ModelNotFoundError` to `404`.
- Modify `app/infrastructure/cache/classification_cache.py`: add `model_version` to cache key API.
- Modify `app/infrastructure/tasks/classification_tasks.py`: use version-aware cache lookup/set and `cache_hit_charge`.
- Modify `app/infrastructure/db/models.py`: add `estimated_cost` and `final_cost` to `ClassificationBatchItemModel`.
- Create `alembic/versions/20260509_0006_mvp_compliance_fix_pack.py`: add batch item cost columns.
- Modify `app/infrastructure/db/repositories/classification_repository.py`: persist batch item costs and add analytics/metrics aggregate helpers.
- Modify `app/infrastructure/db/repositories/billing_repository.py`: add `charge_cache_hit()` and loyalty bootstrap/recalculation methods.
- Modify `app/infrastructure/tasks/maintenance_tasks.py`: implement real loyalty recalculation.
- Create `app/schemas/analytics.py`: response schemas for analytics.
- Create `app/application/analytics/use_cases.py`: user-scoped analytics service.
- Create `app/api/v1/analytics.py`: authenticated analytics routes.
- Modify `app/api/v1/router.py`: include analytics router.
- Create `app/infrastructure/monitoring/persisted_metrics.py`: DB-derived Prometheus metric rendering.
- Modify `app/main.py`: append DB-derived worker/cache metrics to `/metrics`.
- Modify `Makefile`: add `coverage` target if missing.
- Add/update focused tests under `tests/unit` and `tests/integration`.

## Implementation Rules

- Use task id `MVP-FIX` for commits.
- Work in the current branch and current checkout only.
- Do not use subagents or worktrees.
- Keep changes focused; do not refactor unrelated architecture.
- Run targeted tests after each task and full verification at the end.
- Commit after each completed task group.

---

### Task 1: Dependency, Docker, and Streamlit Foundation

**Files:**
- Modify: `pyproject.toml`
- Modify: `docker-compose.yml`
- Create: `scripts/streamlit_dashboard.py`
- Modify: `tests/unit/test_docker_compose_artifacts.py`
- Create: `tests/unit/test_streamlit_dashboard_artifacts.py`

- [ ] **Step 1: Add failing Docker/Streamlit artifact tests**

Extend `tests/unit/test_docker_compose_artifacts.py`:

```python
def test_compose_declares_required_streamlit_service() -> None:
    compose = yaml.safe_load(Path("docker-compose.yml").read_text())

    streamlit = compose["services"]["streamlit"]

    assert streamlit["build"] == "."
    assert "python -m streamlit run scripts/streamlit_dashboard.py" in streamlit["command"]
    assert streamlit["ports"] == ["${STREAMLIT_PORT:-8501}:8501"]
    assert streamlit["depends_on"]["api"]["condition"] == "service_healthy"
```

Create `tests/unit/test_streamlit_dashboard_artifacts.py`:

```python
from pathlib import Path


def test_streamlit_dashboard_script_exists_and_is_api_backed() -> None:
    script = Path("scripts/streamlit_dashboard.py")

    content = script.read_text()

    assert "import streamlit as st" in content
    assert "API_BASE_URL" in content
    assert "requests" not in content
    assert "urllib.request" in content
```

- [ ] **Step 2: Run targeted tests and verify failure**

Run:

```bash
uv run pytest tests/unit/test_docker_compose_artifacts.py tests/unit/test_streamlit_dashboard_artifacts.py -q
```

Expected: fail because the `streamlit` service and dashboard script are absent.

- [ ] **Step 3: Add dependencies**

Update `pyproject.toml`:

```toml
dependencies = [
    "aiosqlite>=0.20.0",
    "alembic>=1.16.0",
    "asyncpg>=0.30.0",
    "celery[redis]>=5.5.0",
    "fastapi[standard]>=0.115.0",
    "pwdlib[argon2]>=0.2.1",
    "pydantic-settings>=2.9.0",
    "pyjwt>=2.10.0",
    "pyyaml>=6.0.2",
    "redis>=5.2.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "streamlit>=1.38.0",
    "transformers>=4.50.0",
]

[dependency-groups]
dev = [
    "httpx>=0.28.0",
    "pre-commit>=4.2.0",
    "pytest>=8.3.0",
    "pytest-asyncio>=0.26.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.11.0",
    "tavily-cli>=0.1.2",
]
```

Run:

```bash
uv sync
```

Expected: lockfile updates successfully.

- [ ] **Step 4: Add Streamlit service**

Add to `docker-compose.yml`:

```yaml
  streamlit:
    build: .
    command: >-
      uv run python -m streamlit run scripts/streamlit_dashboard.py
      --server.address 0.0.0.0
      --server.port 8501
    env_file: .env.example
    environment:
      API_BASE_URL: http://api:8000
    ports:
      - "${STREAMLIT_PORT:-8501}:8501"
    depends_on:
      api:
        condition: service_healthy
```

- [ ] **Step 5: Create minimal dashboard script**

Create `scripts/streamlit_dashboard.py`:

```python
import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen

import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")


def fetch_json(path: str, token: str | None = None) -> dict:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{API_BASE_URL}{path}", headers=headers)
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


st.set_page_config(page_title="UniClassify", layout="wide")
st.title("UniClassify")

try:
    health = fetch_json("/health")
    models = fetch_json("/api/v1/models")
except URLError as exc:
    st.error(f"API unavailable: {exc}")
    st.stop()

st.subheader("Service")
st.json(health)

st.subheader("Models")
st.json(models)

token = st.text_input("API token", type="password")
if token:
    cols = st.columns(3)
    with cols[0]:
        st.subheader("Balance")
        st.json(fetch_json("/api/v1/billing/balance", token))
    with cols[1]:
        st.subheader("Analytics")
        st.json(fetch_json("/api/v1/analytics/summary", token))
    with cols[2]:
        st.subheader("Usage")
        st.json(fetch_json("/api/v1/analytics/usage", token))
```

- [ ] **Step 6: Run targeted tests**

Run:

```bash
uv run pytest tests/unit/test_docker_compose_artifacts.py tests/unit/test_streamlit_dashboard_artifacts.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add pyproject.toml uv.lock docker-compose.yml scripts/streamlit_dashboard.py tests/unit/test_docker_compose_artifacts.py tests/unit/test_streamlit_dashboard_artifacts.py
git commit -m "feat MVP-FIX: добавить streamlit сервис и coverage зависимости"
```

---

### Task 2: API Contract Limits and Unknown Model Status

**Files:**
- Modify: `app/schemas/classifications.py`
- Modify: `app/application/classifications/use_cases.py`
- Modify: `app/api/v1/classifications.py`
- Modify: `tests/unit/test_classification_api.py`
- Modify: `tests/unit/test_classification_batch_api.py`
- Modify: `tests/unit/test_classification_batch_service.py`

- [ ] **Step 1: Add failing contract tests**

Add tests for limits:

```python
from pydantic import ValidationError

from app.schemas.classifications import ClassificationBatchCreateRequest, ClassificationCreateRequest


def test_single_classification_text_limit_is_5000() -> None:
    ClassificationCreateRequest(model_code="prompt_guard", mode="standard", text="x" * 5000)

    with pytest.raises(ValidationError):
        ClassificationCreateRequest(model_code="prompt_guard", mode="standard", text="x" * 5001)


def test_batch_limit_is_100_items() -> None:
    ClassificationBatchCreateRequest(
        model_code="prompt_guard",
        mode="standard",
        items=["x"] * 100,
    )

    with pytest.raises(ValidationError):
        ClassificationBatchCreateRequest(
            model_code="prompt_guard",
            mode="standard",
            items=["x"] * 101,
        )
```

Add/adjust API test:

```python
async def test_create_classification_unknown_model_returns_404(client, auth_headers) -> None:
    response = await client.post(
        "/api/v1/classifications",
        json={"model_code": "missing_model", "mode": "standard", "text": "hello"},
        headers=auth_headers,
    )

    assert response.status_code == 404
```

Add/adjust service test:

```python
async def test_batch_service_accepts_100_items(classification_service, user_id) -> None:
    result = await classification_service.create_batch(
        user_id=user_id,
        model_code="prompt_guard",
        mode="standard",
        items=[f"text {index}" for index in range(100)],
    )

    assert result["batch"].total_requests == 100
```

- [ ] **Step 2: Run targeted tests and verify failure**

Run:

```bash
uv run pytest tests/unit/test_classification_api.py tests/unit/test_classification_batch_api.py tests/unit/test_classification_batch_service.py -q
```

Expected: fail on old limits and unknown-model `400`.

- [ ] **Step 3: Update schemas**

Modify `app/schemas/classifications.py`:

```python
class ClassificationCreateRequest(BaseModel):
    model_code: str = Field(min_length=1, examples=["prompt_guard"])
    mode: str = Field(min_length=1, examples=["standard"])
    text: str = Field(min_length=1, max_length=5_000)


class ClassificationBatchCreateRequest(BaseModel):
    model_code: str = Field(min_length=1, examples=["prompt_guard"])
    mode: str = Field(min_length=1, examples=["standard"])
    items: list[str] = Field(min_length=1, max_length=100, examples=[["one", "two"]])
```

- [ ] **Step 4: Update service batch guard**

Modify `app/application/classifications/use_cases.py`:

```python
MAX_BATCH_ITEMS = 100

class ClassificationService:
    async def create_batch(
        self,
        *,
        user_id: UUID,
        model_code: str,
        mode: str,
        items: list[str],
    ) -> dict:
        if not items or len(items) > MAX_BATCH_ITEMS:
            raise ClassificationBatchSizeError("Batch size must be between 1 and 100")
```

- [ ] **Step 5: Map unknown model to 404**

Modify `app/api/v1/classifications.py`:

```python
    except ModelNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except UnsupportedModeError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
```

Apply the same split to the batch endpoint. Keep `sync-preview` unchanged unless tests explicitly cover it.

- [ ] **Step 6: Run targeted tests**

Run:

```bash
uv run pytest tests/unit/test_classification_api.py tests/unit/test_classification_batch_api.py tests/unit/test_classification_batch_service.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add app/schemas/classifications.py app/application/classifications/use_cases.py app/api/v1/classifications.py tests/unit/test_classification_api.py tests/unit/test_classification_batch_api.py tests/unit/test_classification_batch_service.py
git commit -m "fix MVP-FIX: привести classification api к контракту тз"
```

---

### Task 3: Batch Item Cost Persistence

**Files:**
- Modify: `app/infrastructure/db/models.py`
- Create: `alembic/versions/20260509_0006_mvp_compliance_fix_pack.py`
- Modify: `app/infrastructure/db/repositories/classification_repository.py`
- Modify: `app/infrastructure/tasks/classification_tasks.py`
- Modify: `tests/unit/test_classification_batch_item_models.py`
- Create: `tests/integration/test_classification_batch_item_costs.py`

- [ ] **Step 1: Add failing model/repository tests**

Update model test:

```python
def test_batch_item_model_tracks_costs() -> None:
    item = ClassificationBatchItemModel(
        batch_id=uuid4(),
        classification_request_id=uuid4(),
        item_index=0,
        estimated_cost=7,
    )

    assert item.estimated_cost == 7
    assert item.final_cost is None
```

Create integration test:

```python
async def test_batch_item_costs_are_created_and_finalized(session_factory) -> None:
    async with session_factory() as session:
        user = await UserRepository(session).create_user_with_balance(
            email="batch-cost@example.com",
            hashed_password="hashed",
            initial_credits=0,
        )
        batch = await ClassificationRepository(session).create_batch(
            user_id=user.id,
            total_requests=1,
            estimated_cost=7,
        )
        request = await ClassificationRepository(session).create_request(
            user_id=user.id,
            batch_id=batch.id,
            model_code="prompt_guard",
            mode="standard",
            input_text="hello",
            estimated_cost=7,
        )
        item = await ClassificationRepository(session).create_batch_item(
            batch_id=batch.id,
            classification_request_id=request.id,
            item_index=0,
            estimated_cost=7,
        )
        await ClassificationRepository(session).mark_batch_item_completed(
            request.id,
            final_cost=5,
        )
        await session.commit()

    async with session_factory() as session:
        item = await ClassificationRepository(session).get_batch_item_by_request_id(request.id)
        assert item.estimated_cost == 7
        assert item.final_cost == 5
```

- [ ] **Step 2: Run targeted tests and verify failure**

Run:

```bash
uv run pytest tests/unit/test_classification_batch_item_models.py tests/integration/test_classification_batch_item_costs.py -q
```

Expected: fail because columns and method signatures are absent.

- [ ] **Step 3: Add DB model fields**

Modify `ClassificationBatchItemModel`:

```python
    estimated_cost: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    final_cost: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

Add constructor defaults:

```python
        if self.estimated_cost is None:
            self.estimated_cost = 0
```

- [ ] **Step 4: Add migration**

Create `alembic/versions/20260509_0006_mvp_compliance_fix_pack.py`:

```python
"""add mvp compliance batch item costs

Revision ID: 20260509_0006
Revises: 20260509_0005
Create Date: 2026-05-09 00:06:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260509_0006"
down_revision: str | None = "20260509_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "classification_batch_items",
        sa.Column("estimated_cost", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "classification_batch_items",
        sa.Column("final_cost", sa.Integer(), nullable=True),
    )
    op.alter_column("classification_batch_items", "estimated_cost", server_default=None)


def downgrade() -> None:
    op.drop_column("classification_batch_items", "final_cost")
    op.drop_column("classification_batch_items", "estimated_cost")
```

- [ ] **Step 5: Update repository methods**

Modify `create_batch_item()` signature and body:

```python
    async def create_batch_item(
        self,
        *,
        batch_id: UUID,
        classification_request_id: UUID,
        item_index: int,
        estimated_cost: int,
    ) -> ClassificationBatchItemModel:
        item = ClassificationBatchItemModel(
            batch_id=batch_id,
            classification_request_id=classification_request_id,
            item_index=item_index,
            estimated_cost=estimated_cost,
            status=ClassificationStatus.PENDING.value,
        )
```

Modify completed marker:

```python
    async def mark_batch_item_completed(self, request_id: UUID, final_cost: int | None = None) -> None:
        item = await self.get_batch_item_by_request_id(request_id)
        if item is not None:
            item.status = ClassificationStatus.COMPLETED.value
            item.final_cost = final_cost
            item.completed_at = datetime.now(UTC)
            item.error_message = None
            await self.session.flush()
```

- [ ] **Step 6: Update callers**

In `ClassificationService.create_batch()`, pass:

```python
estimated_cost=estimated_cost_per_item,
```

In `process_classification_request()`, pass:

```python
await repository.mark_batch_item_completed(request.id, final_cost=final_cost)
```

- [ ] **Step 7: Run targeted tests**

Run:

```bash
uv run pytest tests/unit/test_classification_batch_item_models.py tests/integration/test_classification_batch_item_costs.py -q
```

Expected: pass.

- [ ] **Step 8: Commit**

Run:

```bash
git add app/infrastructure/db/models.py alembic/versions/20260509_0006_mvp_compliance_fix_pack.py app/infrastructure/db/repositories/classification_repository.py app/application/classifications/use_cases.py app/infrastructure/tasks/classification_tasks.py tests/unit/test_classification_batch_item_models.py tests/integration/test_classification_batch_item_costs.py
git commit -m "feat MVP-FIX: сохранять стоимость batch items"
```

---

### Task 4: Loyalty Recalculation and Discounted Classification Costs

**Files:**
- Modify: `app/infrastructure/db/repositories/billing_repository.py`
- Modify: `app/infrastructure/tasks/maintenance_tasks.py`
- Modify: `app/application/classifications/use_cases.py`
- Modify: `tests/integration/test_maintenance_tasks.py`
- Modify: `tests/unit/test_classification_service.py`
- Modify: `tests/unit/test_classification_batch_service.py`

- [ ] **Step 1: Add failing loyalty tests**

Add maintenance test:

```python
async def test_recalculate_loyalty_tiers_bootstraps_and_updates_user(session_factory) -> None:
    async with session_factory() as session:
        user = await UserRepository(session).create_user_with_balance(
            email="loyalty@example.com",
            hashed_password="hashed",
            initial_credits=0,
        )
        repository = ClassificationRepository(session)
        for index in range(25):
            request = await repository.create_request(
                user_id=user.id,
                model_code="prompt_guard",
                mode="standard",
                input_text=f"text {index}",
                estimated_cost=7,
            )
            request.status = "completed"
            request.final_cost = 7
            request.completed_at = datetime.now(UTC)
        await session.commit()

    result = await recalculate_loyalty_tiers_once(session_factory=session_factory)

    assert result["updated"] == 1
    async with session_factory() as session:
        refreshed = await session.get(UserModel, user.id)
        tier = await session.get(LoyaltyTierModel, refreshed.loyalty_tier_id)
        assert tier.code in {"silver", "gold"}
```

Add service test:

```python
async def test_classification_service_applies_loyalty_discount(session, user_with_balance, registry):
    tier = LoyaltyTierModel(
        code="silver",
        name="Silver",
        min_monthly_predictions=10,
        discount_percent=10,
    )
    session.add(tier)
    user_with_balance.loyalty_tier_id = tier.id
    await session.flush()

    service = ClassificationService(
        repository=ClassificationRepository(session),
        billing_repository=BillingRepository(session),
        model_registry=registry,
        task_sender=None,
    )

    request = await service.create_classification(
        user_id=user_with_balance.id,
        model_code="prompt_guard",
        mode="standard",
        text="hello",
    )

    assert request.estimated_cost == 7
```

Use the real configured `prompt_guard` standard cost and expected `ceil(base_cost * 0.9)` in the final assertion if the base cost differs.

- [ ] **Step 2: Run targeted tests and verify failure**

Run:

```bash
uv run pytest tests/integration/test_maintenance_tasks.py tests/unit/test_classification_service.py tests/unit/test_classification_batch_service.py -q
```

Expected: fail because recalculation is a no-op and costs are not discounted.

- [ ] **Step 3: Add loyalty defaults and recalculation methods**

In `BillingRepository`, add:

```python
DEFAULT_LOYALTY_TIERS = (
    {"code": "bronze", "name": "Bronze", "min_monthly_predictions": 0, "discount_percent": 0},
    {"code": "silver", "name": "Silver", "min_monthly_predictions": 20, "discount_percent": 10},
    {"code": "gold", "name": "Gold", "min_monthly_predictions": 100, "discount_percent": 20},
)
```

Add methods:

```python
async def bootstrap_loyalty_tiers(self) -> list[LoyaltyTierModel]:
    result = await self.session.execute(select(LoyaltyTierModel))
    existing = {tier.code: tier for tier in result.scalars().all()}
    for data in DEFAULT_LOYALTY_TIERS:
        if data["code"] not in existing:
            self.session.add(LoyaltyTierModel(**data))
    await self.session.flush()
    result = await self.session.execute(
        select(LoyaltyTierModel)
        .where(LoyaltyTierModel.is_active.is_(True))
        .order_by(LoyaltyTierModel.min_monthly_predictions.desc())
    )
    return list(result.scalars().all())
```

Add `recalculate_loyalty_tiers(period_start, period_end) -> int` using completed `ClassificationRequestModel` rows grouped by user. Select the highest active tier whose threshold is less than or equal to the user's completed request count. When tier changes, update `UserModel.loyalty_tier_id` and add `LoyaltyTierHistoryModel`.

- [ ] **Step 4: Implement maintenance task**

Modify `recalculate_loyalty_tiers_once()` to:

```python
async with session_factory() as session:
    repository = BillingRepository(session)
    period_start, period_end = current_month_window(now or datetime.now(UTC))
    updated = await repository.recalculate_loyalty_tiers(
        period_start=period_start,
        period_end=period_end,
    )
    await session.commit()
    return {"updated": updated, "period_start": period_start.isoformat(), "period_end": period_end.isoformat()}
```

- [ ] **Step 5: Apply discounts in classification service**

In `ClassificationService`, add helper:

```python
    async def _estimate_cost(self, *, user_id: UUID, model_code: str, mode: str) -> int:
        from app.domain.billing.services import calculate_discounted_cost

        base_cost = self.model_registry.get_cost(model_code, mode)
        tier = await self.billing_repository.get_loyalty_tier(user_id)
        discount_percent = tier.discount_percent if tier is not None else 0
        return calculate_discounted_cost(
            base_cost=base_cost,
            discount_percent=discount_percent,
        )
```

Use `_estimate_cost()` in both `create_classification()` and `create_batch()`.

- [ ] **Step 6: Run targeted tests**

Run:

```bash
uv run pytest tests/integration/test_maintenance_tasks.py tests/unit/test_classification_service.py tests/unit/test_classification_batch_service.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add app/infrastructure/db/repositories/billing_repository.py app/infrastructure/tasks/maintenance_tasks.py app/application/classifications/use_cases.py tests/integration/test_maintenance_tasks.py tests/unit/test_classification_service.py tests/unit/test_classification_batch_service.py
git commit -m "feat MVP-FIX: реализовать loyalty tiers и скидки"
```

---

### Task 5: Cache Key Versioning and Cache-Hit Billing

**Files:**
- Modify: `app/infrastructure/cache/classification_cache.py`
- Modify: `app/infrastructure/tasks/classification_tasks.py`
- Modify: `app/infrastructure/db/repositories/billing_repository.py`
- Modify: `tests/unit/test_classification_cache.py`
- Modify: `tests/integration/test_classification_cache_worker.py`

- [ ] **Step 1: Add failing cache tests**

Update cache unit test:

```python
def test_cache_key_includes_model_version() -> None:
    cache = InMemoryClassificationCache()
    result_v1 = CachedClassificationResult(
        label="safe",
        confidence=0.9,
        risk_level="low",
        recommended_action="allow",
        explanation="v1",
        raw_scores={},
        metadata={},
        model_code="prompt_guard",
        model_version="1.0.0",
    )
    result_v2 = CachedClassificationResult(
        label="unsafe",
        confidence=0.9,
        risk_level="high",
        recommended_action="block",
        explanation="v2",
        raw_scores={},
        metadata={},
        model_code="prompt_guard",
        model_version="2.0.0",
    )

    cache.set(model_code="prompt_guard", mode="standard", model_version="1.0.0", text="hello", result=result_v1)
    cache.set(model_code="prompt_guard", mode="standard", model_version="2.0.0", text="hello", result=result_v2)

    assert cache.get(model_code="prompt_guard", mode="standard", model_version="1.0.0", text="hello").label == "safe"
    assert cache.get(model_code="prompt_guard", mode="standard", model_version="2.0.0", text="hello").label == "unsafe"
```

Update worker integration test to assert transaction type:

```python
cache_charge = await billing_repository.get_transaction_by_idempotency_key(
    f"classification:{second_request_id}:cache-hit-charge"
)
assert cache_charge is not None
assert cache_charge.transaction_type == "cache_hit_charge"
```

- [ ] **Step 2: Run targeted tests and verify failure**

Run:

```bash
uv run pytest tests/unit/test_classification_cache.py tests/integration/test_classification_cache_worker.py -q
```

Expected: fail because cache API lacks `model_version` and worker still captures cache hits as inference.

- [ ] **Step 3: Update cache API**

Modify `InMemoryClassificationCache`:

```python
    def build_key(self, *, model_code: str, mode: str, model_version: str, text: str) -> str:
        normalized = " ".join(text.strip().split()).casefold()
        material = f"{model_code}:{mode}:{model_version}:{normalized}"
        digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
        return f"classification:{model_code}:{mode}:{model_version}:{digest}"
```

Require `model_version` in `get()` and `set()` and update all call sites.

- [ ] **Step 4: Add cache-hit charge repository method**

In `BillingRepository`, add:

```python
    async def charge_cache_hit(
        self,
        *,
        user_id: UUID,
        amount: int,
        idempotency_key: str,
        related_transaction_id: UUID,
        description: str,
        classification_request_id: UUID | None = None,
    ) -> BillingTransactionModel:
        existing = await self._get_transaction_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing
        if amount <= 0:
            raise ValueError("amount must be positive")

        balance = await self._get_balance_for_update(user_id)
        if balance.reserved_balance < amount:
            raise InsufficientCreditsError("Insufficient reserved credits")
        balance.reserved_balance -= amount
        balance.updated_at = datetime.now(UTC)

        return await self._create_transaction(
            user_id=user_id,
            amount=-amount,
            transaction_type=BillingTransactionType.CACHE_HIT_CHARGE,
            idempotency_key=idempotency_key,
            description=description,
            related_transaction_id=related_transaction_id,
            classification_request_id=classification_request_id,
        )
```

- [ ] **Step 5: Update worker flow**

Before cache lookup, resolve classifier once to get model version:

```python
classifier = registry.get(request.model_code)
cached_result = cache.get(
    model_code=request.model_code,
    mode=request.mode,
    model_version=classifier.model_version,
    text=request.input_text,
)
```

For cache hit, call:

```python
await billing_repository.charge_cache_hit(
    user_id=request.user_id,
    amount=final_cost,
    idempotency_key=f"classification:{request.id}:cache-hit-charge",
    related_transaction_id=hold.id,
    description=f"Charge cache hit for classification {request.id}",
    classification_request_id=request.id,
)
```

For non-cache hit, keep `capture_reserved_credits()`.

When setting cache:

```python
cache.set(
    model_code=request.model_code,
    mode=request.mode,
    model_version=model_version,
    text=request.input_text,
    result=CachedClassificationResult.from_output(
        output=output,
        model_code=model_code,
        model_version=model_version,
    ),
)
```

- [ ] **Step 6: Run targeted tests**

Run:

```bash
uv run pytest tests/unit/test_classification_cache.py tests/integration/test_classification_cache_worker.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add app/infrastructure/cache/classification_cache.py app/infrastructure/tasks/classification_tasks.py app/infrastructure/db/repositories/billing_repository.py tests/unit/test_classification_cache.py tests/integration/test_classification_cache_worker.py
git commit -m "fix MVP-FIX: привести cache billing и ключи к контракту"
```

---

### Task 6: Analytics API

**Files:**
- Create: `app/schemas/analytics.py`
- Create: `app/application/analytics/__init__.py`
- Create: `app/application/analytics/use_cases.py`
- Create: `app/api/v1/analytics.py`
- Modify: `app/api/v1/router.py`
- Modify: `app/infrastructure/db/repositories/classification_repository.py`
- Create: `tests/unit/test_analytics_api.py`
- Create: `tests/integration/test_analytics_repository.py`

- [ ] **Step 1: Add failing analytics tests**

Create API route test:

```python
def test_api_router_includes_analytics_routes() -> None:
    route_paths = {route.path for route in api_router.routes}

    assert "/analytics/summary" in route_paths
    assert "/analytics/usage" in route_paths
    assert "/analytics/costs" in route_paths
    assert "/analytics/models" in route_paths
```

Create repository aggregate test:

```python
async def test_analytics_aggregates_are_user_scoped(session_factory) -> None:
    async with session_factory() as session:
        user = await UserRepository(session).create_user_with_balance(
            email="analytics@example.com",
            hashed_password="hashed",
            initial_credits=0,
        )
        other = await UserRepository(session).create_user_with_balance(
            email="other-analytics@example.com",
            hashed_password="hashed",
            initial_credits=0,
        )
        repository = ClassificationRepository(session)
        request = await repository.create_request(
            user_id=user.id,
            model_code="prompt_guard",
            mode="standard",
            input_text="hello",
            estimated_cost=7,
        )
        request.status = "completed"
        request.final_cost = 7
        request.completed_at = datetime.now(UTC)
        other_request = await repository.create_request(
            user_id=other.id,
            model_code="prompt_guard",
            mode="standard",
            input_text="other",
            estimated_cost=7,
        )
        other_request.status = "completed"
        other_request.final_cost = 7
        other_request.completed_at = datetime.now(UTC)
        await session.commit()

    async with session_factory() as session:
        summary = await ClassificationRepository(session).get_user_analytics_summary(user.id)
        assert summary["total_requests"] == 1
        assert summary["completed_requests"] == 1
        assert summary["total_final_cost"] == 7
```

- [ ] **Step 2: Run targeted tests and verify failure**

Run:

```bash
uv run pytest tests/unit/test_analytics_api.py tests/integration/test_analytics_repository.py -q
```

Expected: fail because analytics routes and repository aggregate methods do not exist.

- [ ] **Step 3: Add schemas**

Create `app/schemas/analytics.py`:

```python
from pydantic import BaseModel


class AnalyticsSummaryResponse(BaseModel):
    total_requests: int
    completed_requests: int
    failed_requests: int
    total_estimated_cost: int
    total_final_cost: int
    cache_hits: int


class AnalyticsUsageItem(BaseModel):
    status: str
    count: int


class AnalyticsUsageResponse(BaseModel):
    items: list[AnalyticsUsageItem]


class AnalyticsCostItem(BaseModel):
    transaction_type: str
    amount: int
    count: int


class AnalyticsCostResponse(BaseModel):
    items: list[AnalyticsCostItem]


class AnalyticsModelItem(BaseModel):
    model_code: str
    count: int
    final_cost: int


class AnalyticsModelsResponse(BaseModel):
    items: list[AnalyticsModelItem]
```

- [ ] **Step 4: Add repository aggregate methods**

Add methods to `ClassificationRepository` using SQLAlchemy `select`, `func.count`, `func.coalesce`, `func.sum`, grouped by status/model. Keep methods user-scoped. The implementation should return plain dictionaries with these exact keys:

```python
async def get_user_analytics_summary(self, user_id: UUID) -> dict:
    return {
        "total_requests": total_requests,
        "completed_requests": completed_requests,
        "failed_requests": failed_requests,
        "total_estimated_cost": total_estimated_cost,
        "total_final_cost": total_final_cost,
        "cache_hits": cache_hits,
    }

async def get_user_usage_breakdown(self, user_id: UUID) -> list[dict]:
    return [{"status": status, "count": count} for status, count in rows]

async def get_user_model_breakdown(self, user_id: UUID) -> list[dict]:
    return [
        {"model_code": model_code, "count": count, "final_cost": final_cost}
        for model_code, count, final_cost in rows
    ]
```

Add cost breakdown to `BillingRepository`:

```python
async def get_user_cost_breakdown(self, user_id: UUID) -> list[dict]:
    return [
        {"transaction_type": transaction_type, "amount": amount, "count": count}
        for transaction_type, amount, count in rows
    ]
```

- [ ] **Step 5: Add analytics use case**

Create `app/application/analytics/use_cases.py`:

```python
from uuid import UUID

from app.infrastructure.db.repositories.billing_repository import BillingRepository
from app.infrastructure.db.repositories.classification_repository import ClassificationRepository


class AnalyticsService:
    def __init__(
        self,
        *,
        classification_repository: ClassificationRepository,
        billing_repository: BillingRepository,
    ) -> None:
        self.classification_repository = classification_repository
        self.billing_repository = billing_repository

    async def summary(self, user_id: UUID) -> dict:
        return await self.classification_repository.get_user_analytics_summary(user_id)

    async def usage(self, user_id: UUID) -> list[dict]:
        return await self.classification_repository.get_user_usage_breakdown(user_id)

    async def costs(self, user_id: UUID) -> list[dict]:
        return await self.billing_repository.get_user_cost_breakdown(user_id)

    async def models(self, user_id: UUID) -> list[dict]:
        return await self.classification_repository.get_user_model_breakdown(user_id)
```

- [ ] **Step 6: Add router**

Create `app/api/v1/analytics.py` with authenticated routes:

```python
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUserDep, DbSessionDep
from app.application.analytics.use_cases import AnalyticsService
from app.infrastructure.db.repositories.billing_repository import BillingRepository
from app.infrastructure.db.repositories.classification_repository import ClassificationRepository
from app.schemas.analytics import (
    AnalyticsCostResponse,
    AnalyticsModelsResponse,
    AnalyticsSummaryResponse,
    AnalyticsUsageResponse,
)

router = APIRouter()


def get_analytics_service(session: DbSessionDep) -> AnalyticsService:
    return AnalyticsService(
        classification_repository=ClassificationRepository(session),
        billing_repository=BillingRepository(session),
    )


AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]


@router.get("/summary")
async def analytics_summary(current_user: CurrentUserDep, service: AnalyticsServiceDep) -> AnalyticsSummaryResponse:
    return AnalyticsSummaryResponse(**await service.summary(current_user.id))
```

Add the other three routes with the response schemas.

- [ ] **Step 7: Include router**

Modify `app/api/v1/router.py`:

```python
from app.api.v1 import admin, analytics, auth, billing, classifications, models

api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
```

- [ ] **Step 8: Run targeted tests**

Run:

```bash
uv run pytest tests/unit/test_analytics_api.py tests/integration/test_analytics_repository.py -q
```

Expected: pass.

- [ ] **Step 9: Commit**

Run:

```bash
git add app/schemas/analytics.py app/application/analytics app/api/v1/analytics.py app/api/v1/router.py app/infrastructure/db/repositories/classification_repository.py app/infrastructure/db/repositories/billing_repository.py tests/unit/test_analytics_api.py tests/integration/test_analytics_repository.py
git commit -m "feat MVP-FIX: добавить analytics api"
```

---

### Task 7: DB-Derived Worker and Cache Metrics

**Files:**
- Create: `app/infrastructure/monitoring/persisted_metrics.py`
- Modify: `app/main.py`
- Modify: `tests/unit/test_metrics_endpoint.py`
- Create: `tests/integration/test_persisted_metrics.py`

- [ ] **Step 1: Add failing persisted metrics tests**

Create integration test:

```python
async def test_persisted_worker_metrics_render_from_db(session_factory) -> None:
    async with session_factory() as session:
        user = await UserRepository(session).create_user_with_balance(
            email="metrics@example.com",
            hashed_password="hashed",
            initial_credits=0,
        )
        repository = ClassificationRepository(session)
        request = await repository.create_request(
            user_id=user.id,
            model_code="prompt_guard",
            mode="standard",
            input_text="hello",
            estimated_cost=7,
        )
        request.status = "completed"
        request.final_cost = 1
        request.completed_at = datetime.now(UTC)
        await repository.save_success(
            request=request,
            output=ClassificationOutput(
                label="safe",
                confidence=0.9,
                risk_level="low",
                recommended_action="allow",
                explanation="ok",
                raw_scores={},
                metadata={"cache_hit": True},
            ),
            model_code="prompt_guard",
            model_version="1.0.0",
            final_cost=1,
        )
        await session.commit()

    async with session_factory() as session:
        rendered = await render_persisted_prometheus_metrics(session)

    assert 'uniclassify_worker_outcomes_total{model_code="prompt_guard",status="completed",cache_hit="true"} 1' in rendered
    assert 'uniclassify_cache_hits_total{model_code="prompt_guard",status="completed"} 1' in rendered
```

- [ ] **Step 2: Run targeted tests and verify failure**

Run:

```bash
uv run pytest tests/unit/test_metrics_endpoint.py tests/integration/test_persisted_metrics.py -q
```

Expected: fail because persisted metrics renderer does not exist.

- [ ] **Step 3: Add persisted metrics renderer**

Create `app/infrastructure/monitoring/persisted_metrics.py`:

```python
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import ClassificationRequestModel, ClassificationResultModel


async def render_persisted_prometheus_metrics(session: AsyncSession) -> str:
    statement = (
        select(
            ClassificationRequestModel.model_code,
            ClassificationRequestModel.status,
            func.coalesce(ClassificationResultModel.result_metadata["cache_hit"].as_boolean(), False),
            func.count(ClassificationRequestModel.id),
        )
        .outerjoin(ClassificationResultModel, ClassificationResultModel.request_id == ClassificationRequestModel.id)
        .group_by(
            ClassificationRequestModel.model_code,
            ClassificationRequestModel.status,
            func.coalesce(ClassificationResultModel.result_metadata["cache_hit"].as_boolean(), False),
        )
    )
    result = await session.execute(statement)
    lines = [
        "# HELP uniclassify_worker_outcomes_total Persisted classification worker outcomes.",
        "# TYPE uniclassify_worker_outcomes_total counter",
    ]
    cache_lines = [
        "# HELP uniclassify_cache_hits_total Persisted classification cache hits.",
        "# TYPE uniclassify_cache_hits_total counter",
    ]
    for model_code, status, cache_hit, count in result.all():
        cache_hit_label = str(bool(cache_hit)).lower()
        lines.append(
            f'uniclassify_worker_outcomes_total{{model_code="{model_code}",status="{status}",cache_hit="{cache_hit_label}"}} {count}'
        )
        if cache_hit:
            cache_lines.append(
                f'uniclassify_cache_hits_total{{model_code="{model_code}",status="{status}"}} {count}'
            )
    return "\n".join(lines + cache_lines) + "\n"
```

If SQLite JSON boolean extraction differs, adjust implementation with a dialect-neutral Python aggregation query over selected rows.

- [ ] **Step 4: Append persisted metrics in `/metrics`**

Modify `app/main.py`:

```python
from app.infrastructure.db.session import AsyncSessionLocal
from app.infrastructure.monitoring.persisted_metrics import render_persisted_prometheus_metrics

    @app.get("/metrics", tags=["monitoring"], summary="Prometheus metrics")
    async def metrics() -> PlainTextResponse:
        rendered = metrics_registry.render_prometheus()
        try:
            async with AsyncSessionLocal() as session:
                rendered += await render_persisted_prometheus_metrics(session)
        except Exception:
            rendered += "# persisted metrics unavailable\n"
        return PlainTextResponse(rendered)
```

- [ ] **Step 5: Run targeted tests**

Run:

```bash
uv run pytest tests/unit/test_metrics_endpoint.py tests/integration/test_persisted_metrics.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

Run:

```bash
git add app/infrastructure/monitoring/persisted_metrics.py app/main.py tests/unit/test_metrics_endpoint.py tests/integration/test_persisted_metrics.py
git commit -m "feat MVP-FIX: экспортировать worker metrics из бд"
```

---

### Task 8: Coverage Gate and Final Verification

**Files:**
- Modify: `Makefile`
- Optionally create: `.coveragerc`
- Modify tests only if coverage is below 70 after enabling `pytest-cov`.

- [ ] **Step 1: Add coverage target**

Modify `Makefile`:

```makefile
.PHONY: coverage

coverage:
	uv run pytest --cov=app --cov-fail-under=70
```

- [ ] **Step 2: Run full local verification**

Run:

```bash
uv run ruff check .
uv run pytest -q
uv run pytest --cov=app --cov-fail-under=70
uv run python -m compileall app tests alembic scripts
docker compose config --services
```

Expected:

- Ruff passes.
- Pytest passes.
- Coverage passes with threshold 70.
- Compileall passes.
- Compose service list includes `streamlit`.

- [ ] **Step 3: If coverage fails below 70, add focused tests**

Only add tests for real untested behavior introduced by this plan:

- analytics aggregation edge cases;
- loyalty no-change and downgrade/upgrade cases;
- cache-hit billing idempotency;
- metrics rendering with no rows;
- Streamlit artifact import safety.

Run coverage again:

```bash
uv run pytest --cov=app --cov-fail-under=70
```

Expected: pass.

- [ ] **Step 4: Run optional Docker smoke**

Run:

```bash
docker compose up -d --build
uv run alembic upgrade head
curl -fsS http://127.0.0.1:${API_PORT:-8000}/health
curl -fsS http://127.0.0.1:${STREAMLIT_PORT:-8501}/_stcore/health
curl -fsS http://127.0.0.1:${API_PORT:-8000}/metrics
docker compose down -v
```

Expected: all curl checks return successfully and Compose shuts down cleanly.

- [ ] **Step 5: Commit verification artifacts**

Commit only source/test/config changes, not local runtime output:

```bash
git add Makefile .coveragerc tests app scripts docker-compose.yml pyproject.toml uv.lock alembic
git commit -m "test MVP-FIX: добавить coverage gate и финальные проверки"
```

If there are no new changes after previous commits, skip this commit and note that verification passed without additional edits.

---

## Final Review Checklist

- [ ] `docker compose config --services` lists `streamlit`.
- [ ] `uv run pytest --cov=app --cov-fail-under=70` works.
- [ ] Single request with text length 5001 fails validation.
- [ ] Batch with 100 items is accepted by schema and service.
- [ ] Batch with 101 items fails validation.
- [ ] Unknown classification model returns `404`.
- [ ] Cache hit creates `cache_hit_charge`, not `inference_capture`.
- [ ] Cache key includes `model_version`.
- [ ] Batch item rows contain `estimated_cost` and `final_cost`.
- [ ] Loyalty recalculation updates at least one eligible user in tests.
- [ ] Discounted costs are reserved for single and batch classification.
- [ ] `/api/v1/analytics/*` routes are registered and authenticated.
- [ ] `/metrics` includes DB-derived worker/cache counters after persisted classifications.
- [ ] `uv run ruff check .` passes.
- [ ] `uv run pytest -q` passes.
- [ ] `uv run python -m compileall app tests alembic scripts` passes.
