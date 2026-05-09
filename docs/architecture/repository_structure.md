# Repository Structure

```text
app/
  api/v1/                  FastAPI routers grouped by product-facing API area
  application/             Use cases and orchestration services
  core/                    Settings, exceptions, security, logging
  domain/                  Pure domain contracts/entities/services
    ml/                    BaseClassifier, DTOs, ModelRegistry
  infrastructure/          Framework and external-service adapters
    db/                    SQLAlchemy sessions/models/repositories
    ml/                    Runtime classifier plugins
    tasks/                 Celery app and task entrypoints
    monitoring/            Metrics exporters
  schemas/                 Pydantic API schemas
config/
  models.yml               Model metadata, labels and pricing
docs/
  analysis/                Requirements extraction
  architecture/            Architecture, decisions, trade-offs
  ml/                      ML strategy
  project/                 Roadmap
  research/                Models and datasets research
ml_training/               Offline training/evaluation scripts per product
streamlit_app/             Dashboard foundation
tests/
  unit/                    Fast deterministic domain/plugin tests
  integration/             DB/API/queue tests
docker-compose.yml         Local production-like topology
Dockerfile                 API/worker image
Makefile                   Repeatable developer commands
```

## Boundary Rules

- API routes call application services, not SQLAlchemy models directly.
- Domain layer does not import FastAPI, SQLAlchemy, Redis, Celery or transformers.
- ML plugins implement `BaseClassifier`.
- Billing logic belongs in domain/application services, not routes or workers.
- Workers call application use cases to preserve transaction/idempotency rules.

## Adding a New Classifier

1. Create `app/infrastructure/ml/<model_code>/classifier.py`.
2. Implement `BaseClassifier`.
3. Add labels, modes and pricing to `config/models.yml`.
4. Register it in the registry loader.
5. Add contract tests covering metadata, supported modes and sample predictions.

