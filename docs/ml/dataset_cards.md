# Dataset Cards

## Purpose

This document records dataset usage decisions for Phase 6 model validation. It does not claim benchmark quality; every dataset needs a license check and leakage review before production training.

## Prompt Safety

Candidate sources:

- Prompt injection and jailbreak corpora from public Hugging Face datasets.
- Toxic/harmful prompt datasets used only for safety label bootstrapping.
- Internal synthetic red-team examples created from documented attack patterns.

MVP use:

- Evaluation-only JSONL slices with fields `text` and `label`.
- Labels mapped to `safe`, `prompt_injection`, and `jailbreak`.

Risks:

- Public jailbreak data can overrepresent popular phrasing and leak benchmark patterns.
- License terms differ by dataset and must be captured before training.
- Safety labels are policy-dependent and may not match platform actions.

## Sentiment and Tone

Candidate sources:

- TweetEval/CardiffNLP-style sentiment data for short social text.
- Multilingual sentiment datasets for Russian and English support.
- Product support examples curated into `negative`, `neutral`, `positive`, and later urgency labels.

MVP use:

- Evaluation-only JSONL slices for adapter smoke tests and regression tracking.
- Separate language tags should be added before comparing multilingual quality.

Risks:

- Social sentiment is not the same distribution as support tickets or prompts.
- Sarcasm, mixed tone, and urgency need separate labels instead of overloaded sentiment classes.

## Quality Gates

- Keep train/eval/test separated by source and collection date.
- Report false positives and false negatives separately for prompt safety.
- Store dataset version, source URL, license, label mapping, and preprocessing notes next to each eval run.
- Do not promote a model from baseline to recommended production without a project-domain eval report.
