# Deployment Runbook

## Local Stack

1. Copy `.env.example` to `.env` and replace `JWT_SECRET_KEY`.
2. Start dependencies and services:

```bash
docker compose up -d --build
```

3. Apply migrations from the API container or local environment:

```bash
uv run alembic upgrade head
```

4. Verify:

```bash
make smoke
```

## Integration Dependencies

For PostgreSQL/Redis-only test dependencies:

```bash
docker compose -f docker-compose.test.yml up -d
```

Use:

- PostgreSQL: `postgresql+asyncpg://uniclassify:uniclassify@localhost:55432/uniclassify_test`
- Redis: `redis://localhost:56379/0`

## Worker Checks

- Confirm API can create classification requests.
- Confirm worker logs include `classification.run`.
- Confirm failed model execution refunds reserved credits.
- Confirm `/metrics` exposes `uniclassify_worker_outcomes_total`.

## Rollback

- Prefer rolling back the application image first.
- Avoid destructive database downgrade in production unless the migration is verified as reversible with current data.
- Model rollback should switch registry/config to the previous `model_version`; historical results remain versioned.

## Smoke and Load

```bash
UNICLASSIFY_BASE_URL=http://127.0.0.1:8000 make smoke
LOAD_TEST_REQUESTS=100 LOAD_TEST_CONCURRENCY=10 make load-test
```

The load script is a lightweight probe, not a full capacity benchmark.

## Acceptance Check

```bash
docker compose up -d --build
docker compose exec api uv run alembic upgrade head
make acceptance
```

The script registers a temporary user, verifies initial credits, runs preview, async and batch classification, checks metrics and reconciles billing transactions.
