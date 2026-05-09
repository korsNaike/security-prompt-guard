# Security Billing Docs Fix Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the review findings around SecurePrompt-only scope docs, cross-user cache leakage, Celery retry behavior, and misleading billing capture history.

**Architecture:** Keep the SecurePrompt-only runtime. Make cache entries user-scoped, make Celery retry path re-raise inference exceptions until retries are exhausted while keeping direct worker processing able to finalize failures, represent capture as a neutral settlement transaction, and update the active technical/final docs to state the SecurePrompt Guard-only scope.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, Celery, in-memory cache abstraction, pytest, Ruff.

---

## File Structure

- Modify `app/infrastructure/cache/classification_cache.py`: add `user_id` to cache keys.
- Modify `app/infrastructure/tasks/classification_tasks.py`: pass `user_id` to cache and add retry-aware failure handling.
- Modify `app/infrastructure/db/repositories/billing_repository.py`: write `inference_capture` amount as `0` because hold already debits current balance.
- Modify `scripts/acceptance_scenario.py`: keep balance reconciliation aligned with neutral capture entries.
- Modify active docs: `docs/TECHNICAL_TASK.MD`, `docs/TECHNICAL_TASK_IMPROVEMENTS.md`, `docs/FINAL_ARCHITECTURE_REPORT.md`.
- Modify tests for user-scoped cache, retry behavior, and neutral capture history.
- Add commit `SPG-007 fix cache retry billing and scope docs`.

### Task 1: Pin Cache, Retry, Billing, And Docs Expectations In Tests

**Files:**
- Modify: `tests/unit/test_classification_cache.py`
- Modify: `tests/integration/test_classification_cache_worker.py`
- Modify: `tests/integration/test_classification_worker.py`
- Modify: `tests/integration/test_billing_repository.py`
- Modify: `tests/unit/test_acceptance_scenario.py`

- [ ] **Step 1: Add user-scoped cache key tests**

Add assertions that equal text/model/version hits for the same user and misses for a different user:

```python
assert first_key == same_user_key
assert first_key != other_user_key
```

- [ ] **Step 2: Add cross-user worker cache test**

Create two users and identical reserved requests. Process both with the same `InMemoryClassificationCache`. Assert both results have `cache_hit is False` and second user's `final_cost == 7`.

- [ ] **Step 3: Add retry-aware worker test**

Call `process_classification_request(..., retry_errors=True)` with a failing registry and assert it raises `RuntimeError` instead of returning `{"status": "failed"}`. Then verify the request is still not finalized as failed by that retry path.

- [ ] **Step 4: Add neutral capture assertions**

In billing repository tests, assert `capture.amount == 0`. In acceptance reconcile test, use `{"transaction_type": "inference_capture", "amount": 0}`.

- [ ] **Step 5: Run focused tests and confirm failures**

Run:

```bash
uv run pytest tests/unit/test_classification_cache.py tests/integration/test_classification_cache_worker.py tests/integration/test_classification_worker.py tests/integration/test_billing_repository.py tests/unit/test_acceptance_scenario.py -q
```

Expected: failures until implementation changes cache keying, retry path, and capture amount.

### Task 2: Make Cache User-Scoped

**Files:**
- Modify: `app/infrastructure/cache/classification_cache.py`
- Modify: `app/infrastructure/tasks/classification_tasks.py`

- [ ] **Step 1: Add `user_id` to cache API**

Change `build_key`, `get`, and `set` to require `user_id: str`. Include `user_id` in the key material:

```python
material = f"{user_id}:{model_code}:{mode}:{model_version}:{normalized}"
```

- [ ] **Step 2: Pass request user id from worker**

In `process_classification_request()`, pass `user_id=str(request.user_id)` to `cache.get()` and `cache.set()`.

- [ ] **Step 3: Run cache tests**

Run:

```bash
uv run pytest tests/unit/test_classification_cache.py tests/integration/test_classification_cache_worker.py -q
```

Expected: pass.

### Task 3: Make Worker Retry Path Raise Until Final Failure

**Files:**
- Modify: `app/infrastructure/tasks/classification_tasks.py`
- Modify: `tests/integration/test_classification_worker.py`

- [ ] **Step 1: Add retry_errors parameter and failure helper**

Add `retry_errors: bool = False` to `process_classification_request()`. In the exception handler, if `retry_errors` is true, re-raise the original exception before marking the request failed/refunding. Move the existing failure/refund logic to a helper, for example:

```python
async def mark_classification_failed_after_retries(request_id: str, error_message: str, *, session_factory=AsyncSessionLocal) -> dict:
    ...
```

- [ ] **Step 2: Replace Celery autoretry swallowing with explicit retry**

Change task decorator to `bind=True`, keep `retry_backoff=True`, `max_retries=3`, and remove `autoretry_for`. In DB-backed task mode, call `process_classification_request(..., retry_errors=True)`. If it raises and `self.request.retries < self.max_retries`, call `raise self.retry(exc=exc)`. If retries are exhausted, call the failure helper and return its failed payload.

- [ ] **Step 3: Run worker tests**

Run:

```bash
uv run pytest tests/integration/test_classification_worker.py tests/unit/test_worker_task.py -q
```

Expected: pass.

### Task 4: Make Capture Transaction Neutral

**Files:**
- Modify: `app/infrastructure/db/repositories/billing_repository.py`
- Modify: `scripts/acceptance_scenario.py`
- Modify: `tests/integration/test_billing_repository.py`
- Modify: `tests/unit/test_acceptance_scenario.py`

- [ ] **Step 1: Change capture transaction amount to zero**

In `capture_reserved_credits()`, keep decreasing `reserved_balance`, but create the transaction with `amount=0`.

- [ ] **Step 2: Keep balance reconciliation explicit**

Ensure `scripts/acceptance_scenario.py` continues to ignore `inference_capture` for current balance reconstruction, and update its test fixture to show capture amount `0`.

- [ ] **Step 3: Run billing tests**

Run:

```bash
uv run pytest tests/integration/test_billing_repository.py tests/unit/test_acceptance_scenario.py tests/integration/test_classification_worker.py -q
```

Expected: pass.

### Task 5: Update Active Scope Docs

**Files:**
- Modify: `docs/TECHNICAL_TASK.MD`
- Modify: `docs/TECHNICAL_TASK_IMPROVEMENTS.md`
- Modify: `docs/FINAL_ARCHITECTURE_REPORT.md`

- [ ] **Step 1: Add scope note to technical task**

At the top of `docs/TECHNICAL_TASK.MD`, add a dated SecurePrompt Guard scope note stating that runtime acceptance now supports `prompt_guard` only and TextMood sections are historical/general-platform context.

- [ ] **Step 2: Update acceptance checklist items**

Replace acceptance items that require `prompt_guard` and `text_mood` with `prompt_guard` only. Replace final summary wording that says the base delivery includes both products with SecurePrompt Guard-only wording.

- [ ] **Step 3: Update final architecture report**

Rewrite `docs/FINAL_ARCHITECTURE_REPORT.md` executive summary and ML model sections to describe SecurePrompt Guard as the runtime product, not a two-product platform.

- [ ] **Step 4: Run docs grep for active contradictions**

Run:

```bash
rg -n "Поддерживаются модели prompt_guard и text_mood|Сервис поддерживает минимум две модели|Rule-based `TextMoodClassifier`|base delivery includes both|В базовой поставке реализуются два продукта" docs/TECHNICAL_TASK.MD docs/TECHNICAL_TASK_IMPROVEMENTS.md docs/FINAL_ARCHITECTURE_REPORT.md
```

Expected: no matches.

### Task 6: Final Verification And Commit

**Files:**
- Verify all changed files.

- [ ] **Step 1: Run active-surface grep**

Run:

```bash
rg -n -i "TextMood|text_mood|sentiment|urgent|angry|toxic|UniClassify|uniclassify" README.md pyproject.toml config app scripts tests dashboards prometheus docker-compose*.yml Dockerfile Makefile .github .env.example
```

Expected: no matches.

- [ ] **Step 2: Run full tests**

Run:

```bash
uv run pytest
```

Expected: pass.

- [ ] **Step 3: Run Ruff**

Run:

```bash
uv run ruff check .
```

Expected: pass.

- [ ] **Step 4: Run compileall**

Run:

```bash
uv run python -m compileall app tests alembic scripts
```

Expected: pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add app/infrastructure/cache/classification_cache.py app/infrastructure/tasks/classification_tasks.py app/infrastructure/db/repositories/billing_repository.py scripts/acceptance_scenario.py tests/unit/test_classification_cache.py tests/integration/test_classification_cache_worker.py tests/integration/test_classification_worker.py tests/integration/test_billing_repository.py tests/unit/test_acceptance_scenario.py docs/TECHNICAL_TASK.MD docs/TECHNICAL_TASK_IMPROVEMENTS.md docs/FINAL_ARCHITECTURE_REPORT.md docs/superpowers/plans/2026-05-09-security-billing-docs-fix-pack.md
git commit -m "SPG-007 fix cache retry billing and scope docs"
```

## Self-Review

- Spec coverage: plan maps to P1 docs scope, P1 cross-user cache side-channel, P2 Celery retry swallowing, and P2 misleading billing capture amount.
- Placeholder scan: no placeholder markers are present.
- Type consistency: cache user id is serialized as string; `inference_capture` remains the transaction type but amount becomes neutral `0`.
