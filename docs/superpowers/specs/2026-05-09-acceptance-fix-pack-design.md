# Acceptance Fix Pack Design

## Context

Full review against `docs/TECHNICAL_TASK.MD`, local checks, Docker startup, real API scenarios and SQL verification showed that the repository is functional but not yet ready for acceptance.

The main gaps are not about adding a new product. They are acceptance blockers in the current MVP:

- Docker Compose does not start reliably out of the box.
- Initial credits are granted twice.
- Batch API accepts `texts`, while the task contract expects `items`.
- Required persistent model catalog tables are missing.
- `config/models.yml` exists but runtime registry is hardcoded.
- Required `classification_batch_items` table is missing.
- Celery Beat runs but has no periodic tasks.
- There is no single executable acceptance scenario that proves Docker, API, worker, billing and metrics together.

## Goal

Bring the current platform to technical-task acceptance quality without a broad rewrite.

The target outcome is:

- clean Docker startup from a fresh checkout;
- correct billing math from registration through async and batch classification;
- API contract aligned with the task;
- persistent model metadata and pricing catalog;
- runtime model registry loaded from configuration;
- batch item persistence;
- real Celery Beat periodic task foundation;
- scripted acceptance verification.

## Chosen Approach

Use an **Acceptance Fix Pack**.

This is a focused hardening pass over the existing architecture. It keeps current domain boundaries and application services, adds missing persistence/contracts where the task requires them, and fixes the critical runtime issues found during review.

Rejected alternatives:

- **Minimal bugfix only:** would fix Docker, balance and `items`, but leave DB/catalog/scheduler gaps. That is not enough for acceptance.
- **Full rewrite to exact spec shape:** would be cleaner on paper but too risky and unnecessary because the existing architecture already has useful boundaries.

## Architecture Decisions

### Docker

Docker Compose should be usable without manual port workarounds.

Changes:

- make host ports configurable with defaults that avoid common local conflicts;
- keep internal service ports stable;
- avoid bind-mounting over the container virtual environment;
- run app commands through `uv run python -m ...` where needed;
- add healthchecks for PostgreSQL, Redis and API;
- use `depends_on.condition: service_healthy` for local orchestration.

### Billing

Initial balance must have a single source of truth.

Decision:

- `UserRepository.create_user_with_balance()` creates `UserBalanceModel(current_balance=0, reserved_balance=0)`;
- `BillingRepository.create_initial_grant()` is the only operation that adds initial credits and writes the billing transaction.

This preserves transaction history and makes SQL reconciliation straightforward.

### Batch API Contract

The canonical request field is `items`.

Decision:

- `ClassificationBatchCreateRequest` accepts `items: list[str]`;
- `texts` may be supported temporarily as a deprecated compatibility alias only if it does not pollute OpenAPI examples;
- all docs and tests use `items`.

### Persistent Model Catalog

The task requires model metadata and pricing to exist in the database.

Add tables:

- `ml_models`;
- `model_pricing`.

Runtime execution still uses `ModelRegistry`, but catalog metadata and pricing are loaded from `config/models.yml` into DB and/or registry through a single config loader path.

### Runtime Model Config Loader

`app/infrastructure/ml/loader.py` should stop hardcoding model classes and prices.

Decision:

- read `settings.model_config_path`;
- parse `config/models.yml`;
- import each `model_class`;
- instantiate the classifier;
- register pricing by mode;
- validate model code, labels, modes and costs.

Errors must be explicit for:

- missing config file;
- malformed YAML;
- missing/invalid class path;
- duplicate model code;
- unsupported classifier contract;
- mode without positive cost.

### Batch Item Persistence

The current `classification_requests.batch_id` shortcut is useful but insufficient for the task.

Add table:

- `classification_batch_items`.

Fields:

- `id`;
- `batch_id`;
- `classification_request_id`;
- `item_index`;
- `status`;
- `created_at`;
- `completed_at`;
- `error_message`.

The existing `classification_requests.batch_id` can remain as a denormalized query shortcut.

### Celery Beat

Beat must schedule real periodic jobs.

Add periodic tasks:

- monthly loyalty recalculation;
- expired promo-code deactivation;
- stale classification cleanup.

The implementation should be idempotent and testable without running a real Beat process.

### Acceptance Verification

Add one scripted acceptance path that validates the product as a system.

The script should check:

- `/health`;
- `/openapi.json`;
- `/api/v1/models`;
- registration;
- login;
- `/api/v1/auth/me`;
- starting balance equals `INITIAL_CREDITS`;
- `sync-preview`;
- async classification completed by worker;
- batch classification using `items`;
- SQL balance reconciliation;
- `/metrics`;
- Prometheus/Grafana health where available.

## Components

### Persistence

New migrations:

- create `ml_models`;
- create `model_pricing`;
- create `classification_batch_items`.

Repository additions:

- model catalog repository;
- model pricing repository;
- batch item lifecycle methods;
- expired promo-code deactivation;
- stale request cleanup;
- loyalty recalculation foundation.

### API

Update:

- batch request schema from `texts` to `items`;
- model catalog endpoints to use persistent catalog data;
- OpenAPI examples to match the task.

### ML Runtime

Update:

- config loader;
- registry construction;
- catalog sync/bootstrap from config.

The default MVP classifiers remain rule-based and deterministic. Hugging Face adapters remain opt-in.

### Infrastructure

Update:

- Docker Compose;
- Makefile targets;
- acceptance script;
- deployment runbook.

## Data Flow

### Registration

1. API validates email/password.
2. User repository creates user and zero balance.
3. Billing repository creates one `initial_grant` transaction.
4. Balance becomes exactly `INITIAL_CREDITS`.

### Batch Classification

1. API receives `items`.
2. Service creates `classification_batches`.
3. Service creates one `classification_requests` row per item.
4. Service creates one `classification_batch_items` row per item.
5. Billing reserves credits per child request.
6. Worker processes child requests.
7. Worker updates request, result and batch item status.
8. Batch aggregate is recalculated from child item/request statuses.

### Model Startup

1. Loader reads `config/models.yml`.
2. Loader validates each model declaration.
3. Loader imports and instantiates classifier classes.
4. Loader registers classifiers and pricing in `ModelRegistry`.
5. Bootstrap/sync stores metadata and pricing in persistent catalog.

## Error Handling

- Docker services expose healthchecks and fail clearly when dependencies are unavailable.
- Invalid model config raises startup/config errors with exact model code and field.
- Batch payloads missing `items` return FastAPI validation errors.
- Billing operations remain idempotent.
- Periodic tasks return structured counts and are safe to rerun.
- Stale processing cleanup should not touch completed requests.

## Testing Strategy

Add tests for:

- no double initial grant;
- Docker Compose artifact checks;
- batch API `items` contract;
- model config loader using temporary YAML;
- model catalog migration and repository;
- catalog sync from config;
- batch item migration and repository;
- worker updates batch item status;
- Beat schedule contains required tasks;
- periodic task handlers are idempotent;
- acceptance script command construction and response validation.

Keep existing verification gates:

```bash
uv run ruff check .
uv run pytest -q
uv run python -m compileall app tests alembic scripts
```

## Implementation Order

1. Docker reliability and balance correctness.
2. Batch `items` API contract.
3. Model catalog tables and config loader.
4. Batch item persistence.
5. Celery Beat periodic task foundation.
6. Acceptance verification script and docs.

This order fixes the highest-risk runtime defects first, then closes task-schema gaps, then adds operational proof.

## Acceptance Criteria

- `docker compose up -d --build` starts API, worker, beat, PostgreSQL, Redis, Prometheus and Grafana without manual command changes.
- New user balance is exactly `INITIAL_CREDITS`.
- Batch API accepts `items`.
- Database contains `ml_models`, `model_pricing`, `classification_batch_items`.
- Runtime model registry is built from `config/models.yml`.
- Celery Beat has configured periodic tasks.
- SQL reconciliation confirms balance equals grants/top-ups/refunds minus captures and active holds.
- `make acceptance` or equivalent script passes on a clean local stack.
- Existing lint, tests and compile checks pass.

## Out of Scope

- Training real ML models.
- Enabling Hugging Face models by default.
- Full production secrets manager integration.
- Distributed tracing.
- Real payment provider integration.
- UI dashboard beyond existing operational artifacts.

## Self-Review

- Placeholder scan: no placeholders or deferred "TBD" requirements.
- Internal consistency: Docker, billing, API, catalog, batch items and Beat decisions match the acceptance findings.
- Scope check: focused on acceptance hardening, not a broad rewrite.
- Ambiguity check: canonical batch field is explicitly `items`; initial credits have exactly one source of truth.
