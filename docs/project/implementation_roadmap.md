# Implementation Roadmap

## Phase 1 - Repository and Architecture Foundation

Goal: Create clean backend skeleton and documentation.

Deliverables:

- FastAPI app skeleton.
- ML contracts and registry.
- Baseline prompt/text classifiers.
- Docker Compose foundation.
- Architecture/research docs.

Dependencies: none.

Risks: foundation may overfit docs without executable tests.

Complexity: Medium.

## Phase 2 - Persistence and Auth

Goal: Implement real user/auth/database foundation.

Deliverables:

- SQLAlchemy models and Alembic migrations.
- Register/login/me endpoints.
- Password hashing and JWT.
- User balance initialization.

Dependencies: Phase 1.

Risks: auth shortcuts can create security debt.

Complexity: Medium.

## Phase 3 - Billing Domain

Goal: Implement transactional credits.

Deliverables:

- Balance service with row locks.
- hold/capture/refund transactions.
- idempotency keys.
- promo code activation.
- loyalty tier schema.

Dependencies: Phase 2 DB/users.

Risks: duplicate capture/refund under retries.

Complexity: High.

## Phase 4 - Async Classification

Goal: Make classification truly asynchronous.

Deliverables:

- Create classification use case.
- Celery task persists status/result.
- Retry and failure refund path.
- GET result and history endpoints.

Dependencies: Phase 3 billing.

Risks: worker transaction boundaries and retry idempotency.

Complexity: High.

## Phase 5 - Batch and Cache

Goal: Add batch processing and cache-hit pricing.

Deliverables:

- Batch API and DB records.
- Child request fan-out.
- partial success aggregation.
- Redis cache for repeated normalized inputs.

Dependencies: Phase 4.

Risks: batch reserve/capture accounting bugs.

Complexity: High.

## Phase 6 - Real ML Model Integration

Goal: Replace baseline rules with validated model plugins.

Deliverables:

- Transformer classifier adapters.
- Model artifact loading.
- Evaluation scripts.
- ONNX export experiment.
- Dataset cards and quality notes.

Dependencies: Phase 1 plugin architecture.

Risks: model quality and license mismatch.

Complexity: Medium-High.

## Phase 7 - Observability, Dashboard and Admin

Goal: Make the system demo-ready.

Deliverables:

- Prometheus metrics.
- Grafana dashboard.
- Streamlit analytics dashboard.
- Admin endpoints for promo codes, users and model catalog.

Dependencies: Phases 3-5.

Risks: dashboard can leak sensitive raw text.

Complexity: Medium.

## Phase 8 - Production Hardening

Goal: Prepare for portfolio-grade deployment.

Deliverables:

- Integration tests with PostgreSQL/Redis.
- Load-test scripts.
- Security review.
- CI enhancements.
- Deployment runbook.

Dependencies: all prior phases.

Risks: infra complexity beyond course scope.

Complexity: Medium.

