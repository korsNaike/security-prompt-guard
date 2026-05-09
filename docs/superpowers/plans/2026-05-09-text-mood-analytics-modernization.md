# TextMood Analytics Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refocus the fork into TextMood Analytics by removing SecurePrompt Guard and replacing the old sentiment/urgency/anger/toxicity classifier with business topic and privacy-safe insight analytics.

**Architecture:** Keep the existing generic platform: FastAPI classification endpoints, model registry, async worker, billing, batch processing, cache, analytics and model catalog. Replace only active product plugins/config/tests/docs: one `text_mood` model remains, now backed by a topic/intent classifier that emits business labels and metadata insights.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, SQLAlchemy/Alembic, Celery, pytest, Ruff, YAML model config.

---

### Task 1: Research And Plan Commit

**Files:**
- Create: `docs/research/text_mood_modernization_research.md`
- Create: `docs/superpowers/plans/2026-05-09-text-mood-analytics-modernization.md`

- [ ] **Step 1: Verify branch**

Run:

```bash
git branch --show-current
```

Expected: `research/text-mood-analytics-modernization`.

- [ ] **Step 2: Commit research and plan**

Run:

```bash
git add docs/research/text_mood_modernization_research.md docs/superpowers/plans/2026-05-09-text-mood-analytics-modernization.md
git commit -m "docs(TMA-001): plan TextMood modernization"
```

Expected: commit succeeds.

### Task 2: Replace Active ML Product Layer

**Files:**
- Modify: `config/models.yml`
- Modify: `app/infrastructure/ml/text_mood/classifier.py`
- Modify: `app/schemas/classifications.py`
- Delete: `app/infrastructure/ml/prompt_guard/classifier.py`
- Delete: `app/infrastructure/ml/prompt_guard/rules.py`
- Delete: `app/infrastructure/ml/hf_prompt_guard/__init__.py`
- Delete: `app/infrastructure/ml/hf_prompt_guard/plugin.py`
- Delete: `app/infrastructure/ml/hf_sentiment/__init__.py`
- Delete: `app/infrastructure/ml/hf_sentiment/plugin.py`

- [ ] **Step 1: Update `config/models.yml`**

Make it contain one active model:

```yaml
models:
  text_mood:
    product_name: TextMood Analytics
    model_class: app.infrastructure.ml.text_mood.classifier.TextMoodClassifier
    version: 0.2.0
    task_type: message_intent_classification
    modes:
      basic:
        cost: 2
      standard:
        cost: 5
    labels:
      - billing_question
      - refund_request
      - technical_issue
      - account_access
      - delivery_or_status
      - feature_request
      - general_question
      - other
```

- [ ] **Step 2: Replace `TextMoodClassifier`**

Implement rule-based intent labels, route actions, risk levels unrelated to sentiment/toxicity, and metadata fields:

```python
metadata={
    "baseline": "rules",
    "mode": input_data.mode,
    "detected_entities": detected_entities,
    "keywords": keywords,
    "redaction_applied": bool(detected_entities),
    "summary_hint": summary_hint,
}
```

- [ ] **Step 3: Remove old product plugins**

Run:

```bash
rm -rf app/infrastructure/ml/prompt_guard app/infrastructure/ml/hf_prompt_guard app/infrastructure/ml/hf_sentiment
```

Expected: removed directories no longer appear in `find app/infrastructure/ml -maxdepth 2 -type d`.

- [ ] **Step 4: Update schema examples**

Change request examples from `prompt_guard` to `text_mood`.

- [ ] **Step 5: Run focused classifier/config tests**

Run:

```bash
uv run pytest tests/unit/test_baseline_classifiers.py tests/unit/test_model_registry.py tests/unit/test_model_config_loader.py -q
```

Expected: fails before test rewrite or passes after Task 3.

### Task 3: Rewrite Tests For New Product Taxonomy

**Files:**
- Modify tests that reference `prompt_guard`, `SecurePrompt Guard`, `prompt_injection`, `jailbreak`, `harmful`, `data_exfiltration`, `suspicious`, `positive`, `negative`, `angry`, `urgent`, `toxic`, `hf_prompt_guard`, `hf_sentiment`.
- Delete obsolete HF plugin tests if they only test deleted plugins.

- [ ] **Step 1: Rewrite baseline classifier tests**

Use examples:

```python
result = classifier.predict(ClassificationInput(
    text="I cannot access my account after password reset",
    model_code="text_mood",
    mode="standard",
))
assert result.label == "account_access"
assert result.recommended_action == "route_account"
assert "keywords" in result.metadata
```

- [ ] **Step 2: Rewrite registry/config/model catalog tests**

Expected active model set:

```python
{"text_mood"}
```

Expected labels include `technical_issue`, `refund_request`, `billing_question`.

- [ ] **Step 3: Rewrite API, worker, repository, analytics and cache fixtures**

Use `text_mood` requests and business labels such as `technical_issue`, `billing_question`, `refund_request`, `account_access`.

- [ ] **Step 4: Remove deleted HF plugin tests**

Delete or rewrite `tests/unit/test_hf_model_plugins.py` so it no longer imports deleted plugin modules.

- [ ] **Step 5: Verify focused tests**

Run:

```bash
uv run pytest tests/unit/test_baseline_classifiers.py tests/unit/test_model_registry.py tests/unit/test_model_config_loader.py tests/unit/test_api_routes.py tests/unit/test_worker_task.py -q
```

Expected: all pass.

- [ ] **Step 6: Commit product layer and tests**

Run:

```bash
git add app config tests
git commit -m "feat(TMA-002): replace classifiers with TextMood intent analytics"
```

Expected: commit succeeds.

### Task 4: Update Docs, Scripts, Project Metadata

**Files:**
- Modify: `pyproject.toml`
- Modify: `app/core/config.py`
- Modify: `README.md`
- Modify: `scripts/acceptance_scenario.py`
- Modify: `scripts/streamlit_dashboard.py`
- Modify: `scripts/dashboard_app.py`
- Modify: active docs under `docs/`

- [ ] **Step 1: Rename package metadata**

Change project name to `text-mood-analytics` and description to topic/intent analytics.

- [ ] **Step 2: Update default app name**

Set `settings.app_name` to `TextMood Analytics`.

- [ ] **Step 3: Rewrite README active product sections**

Remove SecurePrompt Guard and old sentiment/urgency/anger/toxicity descriptions. Present topic/intent analytics and privacy-safe key insights.

- [ ] **Step 4: Update acceptance scenario**

Use `text_mood` in all payloads and assert business labels.

- [ ] **Step 5: Update active architecture/research docs**

Replace active current-state docs with the new TextMood-only product direction. Keep historical `docs/superpowers/*` untouched.

- [ ] **Step 6: Verify no active old terms remain**

Run:

```bash
rg -n "SecurePrompt|prompt_guard|jailbreak|prompt_injection|harmful|data_exfiltration|hf_prompt_guard|hf_sentiment|sentiment|urgency|anger|angry|toxicity|toxic" README.md pyproject.toml app config scripts docs -g '!docs/superpowers/**' -g '!docs/research/2026-05-09-secure-prompt-guard-refocus.md'
```

Expected: no output, except intentionally historical archived docs if added.

- [ ] **Step 7: Commit docs and scripts**

Run:

```bash
git add README.md pyproject.toml app/core/config.py scripts docs config
git commit -m "docs(TMA-003): refocus project on TextMood analytics"
```

Expected: commit succeeds.

### Task 5: Final Verification

**Files:**
- Verify full repository.

- [ ] **Step 1: Run lint**

Run:

```bash
uv run ruff check .
```

Expected: pass.

- [ ] **Step 2: Run tests**

Run:

```bash
uv run pytest
```

Expected: pass.

- [ ] **Step 3: Run compile check**

Run:

```bash
uv run python -m compileall app tests alembic scripts
```

Expected: pass.

- [ ] **Step 4: Commit verification fixes if needed**

If any verification fix changes files:

```bash
git add <changed-files>
git commit -m "fix(TMA-004): complete TextMood modernization verification"
```

Expected: commit succeeds or no changes remain.
