# Technology Decisions

## Backend

Selected: FastAPI.

Why:

- Native OpenAPI and Swagger support match API-first requirements.
- Async request handling fits PostgreSQL async access and queue submission.
- Pydantic schemas provide explicit request/response contracts.

Alternatives:

- Django: stronger built-in admin/auth, but heavier and less clean for API-first ML service boundaries.
- Litestar: capable, but smaller ecosystem for course/demo support.

## Database

Selected: PostgreSQL + SQLAlchemy 2.0 async + asyncpg + Alembic.

Why:

- PostgreSQL supports transactional billing, JSONB metadata, row locks and mature indexing.
- SQLAlchemy 2.0 async is documented for asyncio ORM use: https://docs.sqlalchemy.org/20/orm/extensions/asyncio.html
- Alembic is the standard SQLAlchemy migration tool.

Trade-off:

- Async ORM requires discipline to avoid implicit lazy IO.
- For worker code, sync SQLAlchemy could be simpler; the project keeps one DB stack for consistency.

## Queue

Selected: Celery + Redis for MVP.

Why:

- Celery is mature, supports retries, scheduling through Beat, task routing and multiple brokers.
- Celery docs list Redis as a supported broker/backend: https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/
- Course requirements explicitly mention Celery + Redis as an expected example.

Alternatives:

- Dramatiq: simpler and clean, but less common in course material.
- RQ: easy Redis jobs, weaker scheduling/retry ecosystem.
- arq: async-native, but less mature for complex periodic/background workflows.

## Cache

Selected: Redis.

Why:

- Already needed for Celery broker.
- Supports TTL, atomic counters and distributed cache.

Alternative:

- In-memory cache is simpler but invalid across processes and containers.

## Monitoring

Selected: Prometheus + Grafana.

Why:

- Standard open-source metrics stack.
- Fits containerized deployment and course demonstration.

Trade-off:

- Full tracing stack is deferred. OpenTelemetry can be added later.

## ML Stack

Selected MVP stack:

- Rule-based baseline plugins.
- Transformers-compatible plugin interface.
- Future ONNX/Optimum path for CPU optimization.

Why:

- Rule baseline lets backend, billing, async and plugin architecture work without requiring large model downloads.
- `transformers` is the broadest ecosystem for HF classifiers.
- ONNX is a natural deployment optimization for encoder models.

Alternatives:

- sklearn-only: very CPU friendly, but weaker for semantic prompt-injection generalization.
- sentence-transformers + sklearn: strong custom path, but needs labeled product data.
- LLM moderation: flexible but slower/costlier and harder to self-host.

## Packaging

Selected: uv.

Why:

- Project already uses uv.
- uv is a modern Python package/project manager with a pip-compatible interface: https://docs.astral.sh/uv/

Alternatives:

- Poetry: mature, but slower and introduces a separate dependency style.
- pip-tools: good lock flow, but less complete project workflow.

## Testing

Selected:

- pytest
- pytest-asyncio
- httpx test client
- testcontainers or compose-backed integration tests later

Why:

- pytest is Python standard for backend projects.
- Async tests are required for FastAPI and SQLAlchemy async flows.
- Integration tests should cover row locking/idempotency with real PostgreSQL.

## Infrastructure

Selected:

- Docker Compose for local production-like topology.
- Makefile for repeatable commands.
- pre-commit with Ruff.
- GitHub Actions CI for lint/test foundation.

