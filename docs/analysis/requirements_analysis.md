# Requirements Analysis

Источник: `docs/TECHNICAL_TASK.MD`.

## Business Goals

- Построить универсальную backend-платформу для ML-классификации текста, пригодную для форка в разные продукты.
- Продемонстрировать production-like engineering: API-first backend, ML integration, auth, billing, async queue, DB, Docker, monitoring, tests.
- Поддержать два первых продукта: SecurePrompt Guard и TextMood Analytics.
- Исключить жесткую привязку API и бизнес-логики к одной ML-модели.

## MVP Scope

- FastAPI REST API с OpenAPI/Swagger.
- Пользователи, JWT, роли `user` и `admin`.
- Баланс пользователя, промокоды, loyalty tiers, история транзакций.
- Универсальная классификация одного текста и batch-запросов.
- Асинхронный inference через worker queue.
- Model registry, model metadata, pricing by model/mode.
- PostgreSQL для транзакционных данных.
- Redis для broker/cache.
- Docker Compose для API, worker, scheduler, DB, Redis, Prometheus, Grafana.
- Streamlit dashboard как отдельный демонстрационный UI.

## Mandatory Components

- `BaseClassifier` contract.
- `ModelRegistry`.
- `ClassificationInput` / `ClassificationOutput`.
- Конфигурация моделей через YAML.
- `reserve -> inference -> capture/refund` billing.
- Batch classification с независимой обработкой элементов и `partial_success`.
- Idempotency keys для billing transactions.
- Periodic tasks для loyalty recalculation, promo expiration checks, cleanup.

## Optional Components

- Refresh tokens.
- Advanced mode для не всех моделей.
- Очистка старых failed/cancelled задач.
- Реальный payment gateway исключен из MVP.
- Production model serving через отдельный inference service может быть upgrade path, а не обязательный MVP.

## Architecture Constraints

- Clean architecture: API -> application -> domain -> infrastructure.
- DDD-style separation by domains: users, billing, classifications, ML.
- API не должен содержать `if prompt_guard ... elif text_mood`.
- Новая модель должна подключаться через реализацию `BaseClassifier`, конфиг и registry.
- Финансовые операции должны быть атомарными и идемпотентными.

## Integration Requirements

- PostgreSQL with SQLAlchemy/Alembic.
- Redis for queue broker and cache.
- Celery worker and Celery Beat or documented equivalent.
- Prometheus/Grafana.
- Docker Compose.
- OpenAPI schema at `/openapi.json`, Swagger at `/docs`.

## Non-Functional Requirements

- Extensibility for new classifiers.
- Repeatable local setup.
- Testability of domain/application logic without real ML models.
- Observability for API, workers, billing and inference.
- CPU-friendly MVP inference.
- Documented trade-offs and ADR-like reasoning.

## ML Requirements

- Support multiple labels per product.
- Store model version and metadata.
- Support `basic`, `standard`, `advanced` modes where applicable.
- Provide confidence, risk level, recommended action, explanation and raw scores.
- Keep baseline swappable with transformer/ONNX models later.

## Billing Requirements

- Initial balance: 100 credits.
- Model/mode-specific pricing.
- Loyalty discounts: bronze/silver/gold.
- Promo codes with activation limits and expiry.
- Cache hit charge: 1 credit.
- Atomic reserve/capture/refund.
- Idempotency by operation key.

## Async Requirements

- API creates request, reserves balance and enqueues task.
- Worker sets `processing`, runs classifier, stores result, captures balance.
- Worker refunds reserved credits on inference failure.
- Retry must not duplicate captures/refunds.
- Batch decomposes into individual classification requests.

## Testing Requirements

- Unit tests for model registry, pricing, classifiers, billing service.
- Integration tests for API, DB transactions and queue boundaries.
- Testcontainers or compose-backed tests for PostgreSQL/Redis.
- Contract tests for every plugin classifier.
- CI foundation with lint and tests.

