# Phase 4 Async Classification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist classification requests, run them through an async worker path, store results, and settle reserved credits with capture/refund semantics.

**Architecture:** Add a classification domain slice with a SQLAlchemy repository and application service. The API creates a pending request and reserves credits, while the Celery task loads the request, runs the selected classifier through the registry, persists success/failure, and captures or refunds the hold idempotently.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, Celery, pytest, existing ML registry and billing repository.

---

## File Structure

- Create `app/domain/classifications/entities.py`: request status enum used across repository, schemas, and worker.
- Create `app/infrastructure/db/repositories/classification_repository.py`: persistence operations for request lifecycle and result storage.
- Create `app/application/classifications/use_cases.py`: service orchestration for API create/get/list operations.
- Modify `app/infrastructure/db/models.py`: add `classification_requests` and `classification_results` ORM models.
- Modify `app/infrastructure/db/repositories/billing_repository.py`: expose idempotency-key lookup and persist `classification_request_id`.
- Create `alembic/versions/20260509_0003_create_classification_requests.py`: DB migration for request/result tables and billing FK.
- Modify `app/schemas/classifications.py`: add pending/result/list response schemas.
- Modify `app/api/v1/classifications.py`: authenticated create/get/list endpoints plus existing sync preview.
- Modify `app/infrastructure/tasks/classification_tasks.py`: keep preview-compatible task call and add persisted request processing.
- Add focused tests under `tests/unit` and `tests/integration` for migration, repository, service, API, and worker settlement.

## Tasks

### Task 1: Database and Domain Model

**Files:**
- Create: `app/domain/classifications/entities.py`
- Modify: `app/infrastructure/db/models.py`
- Create: `alembic/versions/20260509_0003_create_classification_requests.py`
- Test: `tests/unit/test_classification_models.py`
- Test: `tests/unit/test_classification_migration.py`

- [ ] Add `ClassificationStatus` enum with `pending`, `processing`, `completed`, `partial_success`, `failed`, `cancelled`.
- [ ] Add ORM models for `ClassificationRequestModel` and `ClassificationResultModel`.
- [ ] Add Alembic migration creating both tables and linking `billing_transactions.classification_request_id`.
- [ ] Test model defaults and migration content.
- [ ] Run `pytest tests/unit/test_classification_models.py tests/unit/test_classification_migration.py -q`.

### Task 2: Repository and Billing Link

**Files:**
- Create: `app/infrastructure/db/repositories/classification_repository.py`
- Modify: `app/infrastructure/db/repositories/billing_repository.py`
- Test: `tests/integration/test_classification_repository.py`

- [ ] Implement request creation, user-scoped lookup, history list, processing mark, success save, and failure mark.
- [ ] Expose `BillingRepository.get_transaction_by_idempotency_key`.
- [ ] Allow billing transaction creation to include `classification_request_id`.
- [ ] Test lifecycle persistence with SQLite async session.
- [ ] Run `pytest tests/integration/test_classification_repository.py -q`.

### Task 3: Application Service and API

**Files:**
- Create: `app/application/classifications/use_cases.py`
- Modify: `app/schemas/classifications.py`
- Modify: `app/api/v1/classifications.py`
- Test: `tests/unit/test_classification_service.py`
- Test: `tests/unit/test_classification_api.py`
- Update: `tests/unit/test_api_routes.py`

- [ ] Implement `ClassificationService.create_classification` to validate model/mode, persist request, reserve credits, and enqueue task.
- [ ] Implement get/list use cases with user ownership checks.
- [ ] Add authenticated POST `/api/v1/classifications`, GET `/api/v1/classifications/{request_id}`, and GET `/api/v1/classifications`.
- [ ] Preserve POST `/api/v1/classifications/sync-preview`.
- [ ] Test service reserve/enqueue behavior and API response shapes.
- [ ] Run `pytest tests/unit/test_classification_service.py tests/unit/test_classification_api.py tests/unit/test_api_routes.py -q`.

### Task 4: Worker Processing and Billing Settlement

**Files:**
- Modify: `app/infrastructure/tasks/classification_tasks.py`
- Test: `tests/unit/test_worker_task.py`
- Test: `tests/integration/test_classification_worker.py`

- [ ] Keep legacy direct task call with explicit `model_code`, `mode`, and `text` returning normalized result.
- [ ] Add persisted processing path that marks request `processing`, runs registry classifier, stores result, and captures reserved credits.
- [ ] Add failure path that marks request `failed` and refunds reserved credits when a hold exists.
- [ ] Test successful settlement and failure refund.
- [ ] Run `pytest tests/unit/test_worker_task.py tests/integration/test_classification_worker.py -q`.

### Task 5: Full Verification and Commit

**Files:**
- All changed files.

- [ ] Run `pytest -q`.
- [ ] Run `python -m compileall app tests alembic`.
- [ ] Remove generated `__pycache__` folders.
- [ ] Run `git status --short` and inspect the final diff.
- [ ] Commit with `feat PHASE4: реализовать async classification flow`.

## Self-Review

- Spec coverage: covers Phase 4 deliverables from roadmap: create classification use case, persisted worker status/result, retry-compatible failure refund path, result/history endpoints.
- Placeholder scan: no TBD or deferred implementation steps.
- Type consistency: request/result/status naming is consistent across models, repository, service, worker, and schemas.
