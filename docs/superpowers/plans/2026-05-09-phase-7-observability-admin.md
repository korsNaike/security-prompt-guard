# Phase 7 Observability Admin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the service demo-ready with Prometheus-compatible metrics, admin endpoints, and dashboard artifacts.

**Architecture:** Add lightweight internal metrics primitives with a `/metrics` exposition endpoint and middleware. Add admin router guarded by existing user role, plus repository methods for user listing and promo-code creation. Keep Streamlit/Grafana as optional artifacts so the backend remains dependency-light.

**Tech Stack:** FastAPI middleware/routes, SQLAlchemy repositories, Prometheus text exposition format, JSON Grafana dashboard, optional Streamlit script.

---

## Tasks

### Task 1: Metrics Foundation

**Files:**
- Create: `app/infrastructure/monitoring/metrics.py`
- Modify: `app/main.py`
- Test: `tests/unit/test_metrics_endpoint.py`

- [ ] Add counters/histogram buckets for HTTP requests and classification worker outcomes.
- [ ] Add middleware recording path/status/duration.
- [ ] Expose `/metrics` as Prometheus-compatible text.
- [ ] Test metrics endpoint shape.

### Task 2: Admin API

**Files:**
- Create: `app/api/v1/admin.py`
- Modify: `app/api/v1/router.py`
- Modify: `app/infrastructure/db/repositories/user_repository.py`
- Modify: `app/infrastructure/db/repositories/billing_repository.py`
- Create: `app/schemas/admin.py`
- Test: `tests/unit/test_admin_api.py`

- [ ] Add admin role guard.
- [ ] Add GET `/api/v1/admin/models`, GET `/api/v1/admin/users`, POST `/api/v1/admin/promo-codes`.
- [ ] Test admin access and non-admin denial.

### Task 3: Dashboard Artifacts

**Files:**
- Create: `dashboards/grafana/uniclassify-overview.json`
- Create: `scripts/dashboard_app.py`
- Create: `docs/observability/dashboard.md`
- Test: `tests/unit/test_dashboard_artifacts.py`

- [ ] Add Grafana dashboard JSON for request counts, latency, and worker outcomes.
- [ ] Add optional Streamlit script with import guard.
- [ ] Document safe dashboard usage and raw-text privacy rule.
- [ ] Test artifact files are present and parseable.

### Task 4: Full Verification and Commit

- [ ] Run `uv run ruff check .`.
- [ ] Run `uv run pytest -q`.
- [ ] Run `uv run python -m compileall app tests alembic scripts`.
- [ ] Remove generated `__pycache__` folders.
- [ ] Commit with `feat PHASE7: добавить observability и admin foundation`.

## Self-Review

- Spec coverage: metrics, dashboard artifacts, and admin endpoints for model catalog, users, and promo codes.
- Placeholder scan: no deferred implementation.
- Type consistency: admin schemas map directly to repository returns and existing user roles.
