# Engineering Trade-offs

## BaseClassifier

Chosen because it creates one stable contract for all ML products. API and billing can work with `ClassificationInput` and `ClassificationOutput` without knowing model internals.

Trade-off: a generic output may not capture every model-specific detail. Product-specific fields should go into `metadata`, while common API fields stay stable.

## Model Registry

Chosen because runtime model lookup, metadata and pricing must be centralized. It prevents hardcoded API branching.

Trade-off: registry must be kept consistent with DB model catalog. The MVP loader is code-based; production should load from config/DB and validate at startup.

## Async Queue

Chosen because ML inference can be slow, fail independently and require retries. A queue keeps API latency predictable and isolates worker scaling.

Trade-off: async flow adds status management and idempotency complexity. For MVP, a `/sync-preview` endpoint exists only as a local/debug preview, not the production path.

## Reserve/Capture Billing

Chosen because charging before inference is unfair on worker failure, and charging only after inference allows users to exceed balance under concurrency. Reserving credits at enqueue time solves both.

Trade-off: requires reserved balance, refund logic and idempotency keys.

## ML Stack

Chosen stack: rule baseline + transformers-compatible plugin interface + ONNX upgrade path.

Reasoning:

- Rule baseline is explainable and deterministic for backend development.
- Transformers keep access to HF classifiers for prompt safety and sentiment.
- ONNX can reduce CPU inference cost after model selection.

Trade-off: adding transformers increases dependency size. Heavy model artifacts should not be loaded in unit tests.

## Queue System

Chosen: Celery + Redis.

Reasoning:

- Meets explicit course expectations.
- Supports retries and periodic tasks.
- Redis is already useful for cache.

Trade-off: Redis broker is fine for MVP; RabbitMQ may be better for high-throughput production queue semantics.

## DB Approach

Chosen: PostgreSQL + SQLAlchemy 2.0 + Alembic.

Reasoning:

- Billing correctness needs ACID transactions and row locks.
- JSONB supports raw scores and metadata.
- Alembic gives migration history for portfolio-grade engineering.

Trade-off: SQLAlchemy async requires careful session management. Integration tests must use real PostgreSQL, not only SQLite.

