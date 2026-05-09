# Phase 5 Batch and Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add batch classification orchestration and a reusable classification result cache with cheaper cache-hit settlement.

**Architecture:** Extend the classification persistence slice with batch records and nullable request `batch_id`. Add a cache abstraction used by the worker before model inference; cache hits store a normal result, capture `settings.cache_hit_cost`, refund the unused hold, and avoid classifier execution.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, Celery worker helper, in-memory cache foundation with Redis-compatible boundary, pytest.

---

## File Structure

- Modify `app/infrastructure/db/models.py`: add `ClassificationBatchModel` and `classification_requests.batch_id`.
- Create `alembic/versions/20260509_0004_create_classification_batches.py`: batch table and request FK.
- Modify `app/infrastructure/db/repositories/classification_repository.py`: batch creation, batch lookup, batch progress aggregation.
- Create `app/infrastructure/cache/classification_cache.py`: cache key and result snapshot abstraction.
- Modify `app/application/classifications/use_cases.py`: batch creation use case and cache-hit cost awareness.
- Modify `app/schemas/classifications.py`: batch request/response schemas.
- Modify `app/api/v1/classifications.py`: POST/GET batch endpoints.
- Modify `app/infrastructure/tasks/classification_tasks.py`: cache lookup/store and partial refund for cheaper cache hits.
- Add unit/integration tests for batch persistence/API and cache settlement.

## Tasks

### Task 1: Batch Persistence

**Files:**
- Modify: `app/infrastructure/db/models.py`
- Create: `alembic/versions/20260509_0004_create_classification_batches.py`
- Test: `tests/unit/test_classification_batch_models.py`
- Test: `tests/unit/test_classification_batch_migration.py`

- [ ] Add `ClassificationBatchModel` with status, counters, estimated/final cost, and timestamps.
- [ ] Add nullable `batch_id` to `ClassificationRequestModel`.
- [ ] Add migration with `classification_batches` table and request FK/index.
- [ ] Test model defaults and migration content.
- [ ] Run `uv run pytest tests/unit/test_classification_batch_models.py tests/unit/test_classification_batch_migration.py -q`.

### Task 2: Batch Repository and Service

**Files:**
- Modify: `app/infrastructure/db/repositories/classification_repository.py`
- Modify: `app/application/classifications/use_cases.py`
- Test: `tests/integration/test_classification_batch_repository.py`
- Test: `tests/unit/test_classification_batch_service.py`

- [ ] Implement batch create/list/get operations and progress aggregation from child request statuses.
- [ ] Implement `create_batch` to create a batch, reserve per child request, enqueue each request, and return request IDs.
- [ ] Test user-scoped batch lookup and service reserve/enqueue behavior.
- [ ] Run `uv run pytest tests/integration/test_classification_batch_repository.py tests/unit/test_classification_batch_service.py -q`.

### Task 3: Batch API

**Files:**
- Modify: `app/schemas/classifications.py`
- Modify: `app/api/v1/classifications.py`
- Test: `tests/unit/test_classification_batch_api.py`

- [ ] Add `ClassificationBatchCreateRequest`, `ClassificationBatchCreateResponse`, and `ClassificationBatchResponse`.
- [ ] Add POST `/api/v1/classifications/batch` and GET `/api/v1/classifications/batch/{batch_id}` before dynamic request routes.
- [ ] Test authenticated batch create/get response shapes.
- [ ] Run `uv run pytest tests/unit/test_classification_batch_api.py -q`.

### Task 4: Result Cache and Cache-Hit Billing

**Files:**
- Create: `app/infrastructure/cache/classification_cache.py`
- Modify: `app/infrastructure/tasks/classification_tasks.py`
- Test: `tests/unit/test_classification_cache.py`
- Test: `tests/integration/test_classification_cache_worker.py`

- [ ] Implement stable cache key from model code, mode, and normalized input text.
- [ ] Store result snapshots after successful model inference.
- [ ] On cache hit, save result with cached metadata, capture `settings.cache_hit_cost`, and refund the unused reserved balance.
- [ ] Test cache key stability and worker cache-hit settlement.
- [ ] Run `uv run pytest tests/unit/test_classification_cache.py tests/integration/test_classification_cache_worker.py -q`.

### Task 5: Full Verification and Commit

**Files:**
- All changed files.

- [ ] Run `uv run ruff check .`.
- [ ] Run `uv run pytest -q`.
- [ ] Run `uv run python -m compileall app tests alembic`.
- [ ] Remove generated `__pycache__` folders.
- [ ] Commit with `feat PHASE5: добавить batch processing и cache-hit billing`.

## Self-Review

- Spec coverage: implements Phase 5 roadmap items: batch API/records, child request fan-out, partial success aggregation, and cache-hit pricing.
- Placeholder scan: all tasks include concrete files, commands, and expected behavior.
- Type consistency: batch/request/cache naming is consistent across migration, ORM, repository, service, API, and worker.
