# Phase 6 Real ML Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add production-safe transformer model plugin foundations, evaluation scripts, ONNX export experiment scaffolding, and dataset quality documentation.

**Architecture:** Keep the app model-agnostic by adding a reusable Hugging Face text-classification adapter that implements the existing `BaseClassifier` contract. Do not download or load heavyweight artifacts during app startup; real models are configured as plugins and loaded lazily only when explicitly instantiated.

**Tech Stack:** existing `transformers`, optional ONNX/Optimum export command, pytest with fake pipelines, JSONL evaluation inputs.

---

## File Structure

- Create `app/infrastructure/ml/common/transformers_text_classifier.py`: generic HF pipeline adapter.
- Create `app/infrastructure/ml/common/model_artifacts.py`: artifact config dataclass and validation.
- Create `app/infrastructure/ml/hf_prompt_guard/plugin.py`: real-model plugin factory for prompt safety.
- Create `app/infrastructure/ml/hf_sentiment/plugin.py`: real-model plugin factory for sentiment/tone.
- Create `scripts/evaluate_classifier.py`: JSONL evaluation runner for registered classifiers.
- Create `scripts/export_onnx.py`: guarded ONNX export experiment entrypoint.
- Create `docs/ml/dataset_cards.md`: MVP dataset usage/quality notes.
- Add unit tests for adapter mapping, artifact validation, and evaluation metrics.

## Tasks

### Task 1: Transformer Adapter

**Files:**
- Create: `app/infrastructure/ml/common/model_artifacts.py`
- Create: `app/infrastructure/ml/common/transformers_text_classifier.py`
- Test: `tests/unit/test_transformers_text_classifier.py`

- [ ] Implement artifact config with model id/path, revision, label mapping, and model version.
- [ ] Implement `TransformersTextClassificationAdapter` that maps pipeline outputs to `ClassificationOutput`.
- [ ] Test with a fake pipeline so tests never download external models.
- [ ] Run `uv run pytest tests/unit/test_transformers_text_classifier.py -q`.

### Task 2: Real Model Plugin Factories

**Files:**
- Create: `app/infrastructure/ml/hf_prompt_guard/plugin.py`
- Create: `app/infrastructure/ml/hf_sentiment/plugin.py`
- Test: `tests/unit/test_hf_model_plugins.py`

- [ ] Add prompt-safety and sentiment plugin factory functions using the generic adapter.
- [ ] Keep factories opt-in and out of the default registry to avoid startup downloads.
- [ ] Test descriptors and supported modes without loading real artifacts.
- [ ] Run `uv run pytest tests/unit/test_hf_model_plugins.py -q`.

### Task 3: Evaluation and ONNX Scripts

**Files:**
- Create: `scripts/evaluate_classifier.py`
- Create: `scripts/export_onnx.py`
- Test: `tests/unit/test_ml_scripts.py`

- [ ] Implement JSONL evaluator with accuracy, per-label counts, and invalid-row reporting.
- [ ] Implement ONNX export script with dependency guard and explicit model/output arguments.
- [ ] Test evaluator on a temp JSONL file.
- [ ] Run `uv run pytest tests/unit/test_ml_scripts.py -q`.

### Task 4: ML Documentation

**Files:**
- Create: `docs/ml/dataset_cards.md`
- Modify: `docs/ml/ml_strategy.md`

- [ ] Document dataset fit, known quality risks, licensing checks, and MVP usage.
- [ ] Document lazy model loading and CPU-first upgrade path.

### Task 5: Full Verification and Commit

- [ ] Run `uv run ruff check .`.
- [ ] Run `uv run pytest -q`.
- [ ] Run `uv run python -m compileall app tests alembic scripts`.
- [ ] Remove generated `__pycache__` folders.
- [ ] Commit with `feat PHASE6: добавить real ML integration foundation`.

## Self-Review

- Spec coverage: transformer adapters, artifact loading boundary, evaluation scripts, ONNX export experiment, and dataset cards are covered.
- Placeholder scan: no deferred implementation steps.
- Type consistency: all adapters implement the existing `BaseClassifier` contract and stay registry-compatible.
