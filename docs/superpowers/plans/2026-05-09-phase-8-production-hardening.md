# Phase 8 Production Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add portfolio-grade hardening artifacts: CI checks, integration environment docs, smoke/load scripts, security review, and deployment runbook.

**Architecture:** Keep hardening lightweight and executable locally. CI should verify lint, tests, compileability, and migration import health. Operational scripts should use the public HTTP API only, so they remain valid across local Docker Compose and deployed environments.

**Tech Stack:** GitHub Actions, Docker Compose, stdlib Python HTTP clients, pytest artifact checks, markdown runbooks.

---

## Tasks

### Task 1: CI and Makefile Hardening

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `Makefile`
- Test: `tests/unit/test_production_artifacts.py`

- [ ] Add compileall and Alembic migration import checks to CI.
- [ ] Add `ci`, `smoke`, and `load-test` Makefile targets.
- [ ] Test CI/Makefile files contain required commands.

### Task 2: Smoke and Load Scripts

**Files:**
- Create: `scripts/smoke_test.py`
- Create: `scripts/load_test.py`
- Test: `tests/unit/test_production_artifacts.py`

- [ ] Add smoke test for `/health`, `/openapi.json`, `/api/v1/models`, and `/metrics`.
- [ ] Add stdlib load probe for `/health` with concurrency and latency summary.
- [ ] Keep scripts configurable through environment variables.

### Task 3: Deployment and Security Docs

**Files:**
- Create: `docs/deployment/runbook.md`
- Create: `docs/security/security_review.md`
- Create: `docker-compose.test.yml`
- Test: `tests/unit/test_production_artifacts.py`

- [ ] Document local Docker startup, migrations, worker checks, metrics, and rollback notes.
- [ ] Document security review: auth, billing, prompt data, admin, secrets, and model supply chain.
- [ ] Add test compose file for PostgreSQL/Redis integration environment.

### Task 4: Full Verification and Commit

- [ ] Run `uv run ruff check .`.
- [ ] Run `uv run pytest -q`.
- [ ] Run `uv run python -m compileall app tests alembic scripts`.
- [ ] Remove generated `__pycache__` folders.
- [ ] Commit with `feat PHASE8: добавить production hardening foundation`.

## Self-Review

- Spec coverage: integration environment, load-test scripts, security review, CI enhancements, and deployment runbook.
- Placeholder scan: no deferred implementation.
- Type consistency: scripts are environment-variable driven and match existing service routes.
