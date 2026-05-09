# UniClassify Platform

Universal backend foundation for ML text-classification products.

The repository is structured as a production-like MVP platform rather than a single hardcoded model service. The core platform owns API, auth, billing, async inference, history, monitoring, and model registry boundaries. Product modules plug in through a shared `BaseClassifier` contract.

Initial product modules:

- `prompt_guard`: SecurePrompt Guard for prompt injection, jailbreak, harmful prompt, and data-exfiltration risk classification.
- `text_mood`: TextMood Analytics for sentiment, urgency, anger, and toxicity classification.

## Local Commands

```bash
uv sync
uv run pytest
uv run fastapi dev app/main.py
docker compose up --build
```

## Key Documentation

- [Final architecture report](docs/FINAL_ARCHITECTURE_REPORT.md)
- [System architecture](docs/architecture/system_architecture.md)
- [Technology decisions](docs/architecture/technology_decisions.md)
- [ML strategy](docs/ml/ml_strategy.md)
- [Repository structure](docs/architecture/repository_structure.md)
- [Implementation roadmap](docs/project/implementation_roadmap.md)
