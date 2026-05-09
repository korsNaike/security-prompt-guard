# MVP Compliance Fix Pack Design

## Context

The latest full test run in `.codex/full-test-runs/20260509T091435Z/` shows that the core product now works: Docker can run after the previous fixes, API auth/billing/classification/batch flows are functional, Celery completes async work, and Prometheus/Grafana respond.

The remaining gaps are not a new product direction. They are contract and acceptance gaps against `docs/TECHNICAL_TASK.MD`:

- Docker Compose does not include the required Streamlit service.
- Loyalty tiers are persisted but not actually recalculated, and discounts are not applied to classification costs.
- Analytics endpoints are absent.
- The coverage gate cannot run because `pytest-cov` is missing.
- Cache-hit billing uses the wrong transaction semantics.
- Cache keys do not include `model_version`.
- Classification input limits drift from the task contract.
- `classification_batch_items` lacks per-item costs.
- Worker/cache metrics are process-local and are not visible through the API `/metrics` endpoint scraped by Prometheus.
- Unknown model errors in classification creation return `400`, while the task expects `404`.

## Goal

Close the remaining MVP acceptance gaps with focused production-like changes while preserving the existing FastAPI, SQLAlchemy, Celery, billing, model registry and catalog architecture.

The target outcome is:

- Docker Compose exposes `api`, `worker`, `beat`, `postgres`, `redis`, `prometheus`, `grafana` and `streamlit`.
- Loyalty tier recalculation updates users and tier history deterministically.
- Classification cost estimation and capture apply loyalty discounts consistently.
- Analytics endpoints expose user-scoped usage, cost and model breakdowns.
- Coverage can be verified with `uv run pytest --cov=app --cov-fail-under=70`.
- Cache-hit transactions use `cache_hit_charge`.
- Cache entries are version-aware.
- API input limits match the task: single text up to 5000 characters and batch up to 100 items.
- Batch item rows include `estimated_cost` and `final_cost`.
- `/metrics` exposes worker/cache counters derived from persisted state, not only from the API process memory.
- Unknown model creation errors return `404`.

## Chosen Approach

Use a second focused **MVP Compliance Fix Pack**.

This approach keeps the current architecture and adds the missing compliance pieces in the smallest coherent increments. It avoids a rewrite, but it also avoids superficial patches that only satisfy one HTTP scenario while leaving billing, persistence or observability inconsistent.

Rejected alternatives:

- **Patch only P1 findings:** would leave cache billing, version-aware cache keys, batch item costs and worker metrics inconsistent with the task.
- **Replace observability with full Prometheus multiprocess setup:** useful later, but too much infrastructure for the current Compose-based MVP. Persisted DB-derived metrics are easier to reason about and test now.
- **Build a rich Streamlit product UI:** unnecessary for acceptance. A compact operational dashboard is enough and keeps maintenance cost low.

## Scope

### In Scope

- Streamlit service and a minimal dashboard app.
- Loyalty tier bootstrap, recalculation and discount application.
- User-scoped analytics API.
- Coverage dependency and verification target.
- Cache-hit billing transaction semantics.
- Version-aware classification cache keys.
- Input limit corrections.
- Batch item cost columns and lifecycle updates.
- Persisted metrics export through API `/metrics`.
- `404` mapping for unknown classification models.
- Focused regression tests and Docker smoke verification.

### Out of Scope

- External hosted dashboards.
- A public unauthenticated analytics API.
- Real Hugging Face model downloads in default tests.
- A new queue system.
- A full frontend product beyond the required Streamlit service.
- Historical migration of existing Redis cache entries.

## Architecture Decisions

### Streamlit

Add a `streamlit` service to Docker Compose using the existing application image. The service runs a small dashboard script under `scripts/streamlit_dashboard.py`.

The dashboard should call the HTTP API rather than importing repositories directly. This keeps it as a separate client surface and prevents UI code from depending on internal DB/session details.

### Loyalty

Loyalty tiers should be calculated from persisted classification/billing facts.

Decision:

- bootstrap default tiers if `loyalty_tiers` is empty;
- recalculate users from successful captured classification usage;
- update `users.loyalty_tier_id`;
- append `loyalty_tier_history` when a user's tier changes;
- apply the active tier discount when estimating classification cost.

The discount must affect both single classification and batch child requests because billing reservations are created per request.

### Analytics

Add `/api/v1/analytics` endpoints that are authenticated and user-scoped by default.

Initial endpoints:

- `GET /api/v1/analytics/summary`;
- `GET /api/v1/analytics/usage`;
- `GET /api/v1/analytics/costs`;
- `GET /api/v1/analytics/models`.

The endpoints should use SQL aggregate queries over persisted requests, results and billing transactions. They should not depend on in-memory metrics.

### Coverage

Add `pytest-cov` to the development dependencies and a repeatable target for the task-required coverage check.

Decision:

- keep the threshold at `70`;
- add focused tests for the new compliance features instead of inflating coverage with artificial tests;
- add a coverage config only for legitimate exclusions such as migrations or generated-style scripts if needed.

### Cache Billing

Cache hits should be billed as a first-class billing event.

Decision:

- preserve the existing reserve-then-settle flow;
- when a cached result is used, create a `cache_hit_charge` transaction for the configured cache-hit cost;
- refund the unused reserved amount separately;
- do not label cache-hit settlement as `inference_capture`.

This keeps financial reporting and SQL reconciliation aligned with the task.

### Cache Key

The cache key must include model version to prevent stale results after a model upgrade.

Decision:

- use `model_code`, `mode`, normalized text and `model_version` in the key material;
- keep old cache entries naturally unreachable;
- do not add a migration or Redis purge requirement for old keys.

### Batch Item Costs

`classification_batch_items` should be the item ledger, not only a status table.

Decision:

- add `estimated_cost` and `final_cost`;
- write `estimated_cost` when the child request is created;
- update `final_cost` after worker settlement;
- keep request-level costs as the source of truth for billing and batch item costs as the per-item reporting projection.

### Worker and Cache Metrics

The current in-memory registry is useful only inside one process. Prometheus scrapes the API process, so worker-side counters are invisible.

Decision:

- export worker/cache counters in `/metrics` from persisted classification state;
- derive worker outcomes from `classification_requests` and cache-hit counts from result metadata or billing transactions;
- keep existing in-memory counters as best-effort process-local metrics, but make acceptance rely on DB-derived counters.

This is more deterministic in Docker Compose than Prometheus multiprocess mode and avoids adding another metrics HTTP server to the worker.

### Unknown Model Errors

Classification creation should distinguish missing models from invalid request shape.

Decision:

- map model-not-found errors to `404`;
- keep unsupported mode and malformed input as `400` or `422`;
- apply the same mapping to single and batch flows where relevant.

## Data Flow

### Classification With Loyalty Discount

1. API receives classification request.
2. Application service resolves the model and base mode price.
3. Billing service loads the user's active loyalty tier.
4. Estimated cost is calculated after discount.
5. Billing reserves discounted estimated cost.
6. Worker performs cache lookup or inference.
7. Worker settles the request with either `inference_capture` or `cache_hit_charge`.
8. Refund transaction returns any unused reservation.
9. Request, result, batch item and metrics projection remain SQL-reconcilable.

### Cache Hit Settlement

1. Worker computes a version-aware cache key.
2. Cache returns a stored result.
3. Worker creates a result row with `metadata.cache_hit=true`.
4. Billing creates `cache_hit_charge` for the cache-hit cost.
5. Billing refunds the difference between reserved and cache-hit cost.
6. Request final cost becomes the cache-hit cost.

### Metrics Export

1. Worker updates persisted request/result/billing records as part of normal processing.
2. API `/metrics` renders standard in-memory API counters.
3. API additionally queries aggregate persisted classification state.
4. Prometheus sees worker outcomes and cache-hit counters from the API scrape target.

## Testing Strategy

Regression tests should cover:

- Docker Compose includes the `streamlit` service.
- Streamlit dashboard script has a valid entry point.
- loyalty bootstrap/recalculation updates tiers and history;
- discounted costs are reserved for single and batch classifications;
- cache hits create `cache_hit_charge` and refund the difference;
- cache key changes when `model_version` changes;
- request limits enforce 5000 text characters and 100 batch items;
- batch items store estimated and final costs;
- analytics endpoints return user-scoped aggregates;
- `/metrics` contains DB-derived worker/cache counters after persisted events;
- unknown model classification returns `404`;
- coverage command runs with the configured threshold.

Verification commands:

```bash
uv run ruff check .
uv run pytest -q
uv run pytest --cov=app --cov-fail-under=70
uv run python -m compileall app tests alembic scripts
docker compose config --services
```

Docker/live verification should also include:

```bash
docker compose up -d --build
uv run alembic upgrade head
curl -fsS http://127.0.0.1:${API_PORT:-8000}/health
curl -fsS http://127.0.0.1:${STREAMLIT_PORT:-8501}/_stcore/health
curl -fsS http://127.0.0.1:${API_PORT:-8000}/metrics
docker compose down -v
```

## Risks

- Coverage may initially be below 70 after enabling `pytest-cov`. The fix should be real coverage for the new behavior, not lowering the threshold.
- Loyalty rules must remain deterministic because the monthly Celery Beat task may be re-run manually.
- Persisted metrics should avoid expensive full-table scans for large production data. The MVP can use simple aggregate queries, with a future upgrade path to rollup tables.
- Streamlit adds runtime dependency weight. This is acceptable for task compliance, but the dashboard should remain optional in production deployment.

## Acceptance Criteria

- All P1/P2/P3 findings from the latest report are addressed.
- Existing previously-fixed acceptance behavior does not regress.
- Local tests, lint, compileall and coverage gate pass.
- Docker Compose lists and starts `streamlit`.
- SQL reconciliation shows correct initial grant, reserve/capture/refund/cache-hit transaction types.
- `/metrics` includes worker/cache metrics after async or batch processing.
- Work is delivered through small commits using task id `MVP-FIX`.
