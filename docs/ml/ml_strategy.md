# ML Strategy

## Goals

- Keep the platform model-agnostic.
- Make MVP runnable on CPU without large downloads.
- Preserve a clear upgrade path to real transformer classifiers.
- Version every model and include version in cache keys and result records.

## MVP Baseline

Selected baseline:

- `prompt_guard`: deterministic rule-based classifier.
- `text_mood`: deterministic rule-based classifier.

Why:

- Proves architecture, billing and async flow immediately.
- Fast and explainable.
- Avoids fragile demos blocked by GPU/model download issues.
- Keeps tests deterministic.

Limitations:

- Not robust against paraphrased attacks or nuanced sentiment.
- Must be documented as baseline, not production-grade ML quality.

## Recommended Production Models

SecurePrompt Guard:

- Primary upgrade: compact encoder prompt-injection classifier such as Llama Prompt Guard 2 22M/86M, ProtectAI DeBERTa prompt-injection or a domain-finetuned DeBERTa-small.
- Advanced mode: ensemble of rules + encoder classifier + optional external moderation/safety judge.

TextMood Analytics:

- Primary upgrade: fine-tuned encoder classifier for product labels.
- Candidate starting points: DistilBERT for cheap English sentiment, CardiffNLP/TweetEval RoBERTa for social/support-style text, multilingual MiniLM/mDeBERTa when Russian support is required.

## CPU Inference Strategy

- Prefer encoder-only classifiers under ~100-200M parameters for MVP/prototype CPU inference.
- Export selected models to ONNX after validation.
- Quantize only after measuring quality regression.
- Keep max input length bounded and reject or truncate according to product policy.

## Batching Strategy

- API batch request decomposes into child classification requests.
- Worker can later micro-batch by `(model_code, model_version, mode)` for transformer inference.
- Billing remains per item, not per micro-batch.

## Model Loading Strategy

- Lazy load heavy models on first use in each worker process.
- Keep model instances process-local.
- Expose warmup hooks for production workers.
- Rule-based MVP classifiers load immediately.

## Caching Strategy

- Normalize text before hashing.
- Include `model_code`, `mode`, `normalized_text`, `model_version`.
- Store final `ClassificationOutput` plus metadata.
- Cache hit cost is 1 credit and creates normal history.

## Versioning Strategy

- `model_version` is part of model descriptor, DB result and cache key.
- New model versions should be additive deployments.
- Rollback means making previous version active in registry/config and DB catalog.

## Evaluation Strategy

- Keep source-separated train/test/eval splits.
- Track false positives separately from false negatives for prompt safety.
- For TextMood, evaluate business action quality, not only sentiment accuracy.
- Do not compare models solely on public benchmark scores; validate on support/prompt examples close to the product domain.
