# TextMood Analytics Modernization Research

Дата исследования: 2026-05-09

Рабочая копия: `/Users/grinev.kv/PycharmProjects/unik/itmo/ml-services/secure-prompt-guard-fork`

Исходный репозиторий: `/Users/grinev.kv/PycharmProjects/unik/itmo/ml-services/secure-prompt-guard`

Ветка исследования: `research/text-mood-analytics-modernization`

## 1. Цель

Подготовить следующий этап модернизации проекта после локального git-форка:

- убрать из продукта `SecurePrompt Guard`;
- убрать текущую продуктовую логику анализа тональности, срочности, злости и токсичности текста;
- сохранить reusable backend-платформу для платного ML/LLM text analysis сервиса;
- предложить 1-2 продуктовые фичи, которые усиливают `TextMood Analytics` без возврата к safety/sentiment/toxicity use case.

Этот документ является исследовательским. Он не вносит функциональные изменения в код.

## 2. Git-Форк

Форк уже присутствует как отдельный git-клон:

```text
/Users/grinev.kv/PycharmProjects/unik/itmo/ml-services/secure-prompt-guard-fork
```

Проверка показала:

- `origin` указывает на локальный исходник `secure-prompt-guard`;
- форк находится на том же коммите, что и исходник: `60ee36f`;
- создана отдельная ветка `research/text-mood-analytics-modernization`;
- исходный репозиторий не изменялся.

## 3. Общее Состояние Проекта

Проект фактически является `UniClassify Platform`: универсальным backend-сервисом для текстовой классификации с платной моделью использования.

Основной стек:

- FastAPI API и OpenAPI;
- SQLAlchemy 2.0 async, Alembic, PostgreSQL;
- Redis, Celery worker, Celery beat;
- JWT auth, users, roles;
- credits billing: reserve, capture, refund;
- model catalog и pricing по `model_code`/`mode`;
- batch processing;
- inference cache;
- analytics endpoints;
- admin endpoints;
- Streamlit, Prometheus, Grafana;
- 60 тестовых файлов, около 10.4k строк в `app`, `tests`, `scripts`, `alembic`, `docs`, `config` без `docs/superpowers`.

Ключевой архитектурный вывод: платформа в целом не привязана к `SecurePrompt Guard` или к текущему `TextMoodClassifier`. Жесткая продуктовая специфика сосредоточена в model config, ML-плагинах, тестах, документации, demo scripts и отдельных OpenAPI examples.

## 4. Что Нужно Сохранить

Следующие части стоит сохранить как платформенное ядро:

- `app/api/v1/auth.py`, `billing.py`, `admin.py`, `analytics.py`, `models.py`;
- `app/api/v1/classifications.py` как текущий generic inference API, либо позднее переименовать в `/analyses` отдельным этапом;
- `app/application/*` use cases;
- `app/domain/ml/classifier_contracts.py`;
- `app/domain/ml/model_registry.py`;
- `app/infrastructure/ml/config_loader.py` и `loader.py`;
- `app/infrastructure/tasks/classification_tasks.py`;
- `app/infrastructure/cache/classification_cache.py`;
- DB schema для requests/results/batches/model catalog/billing/users/audit logs;
- Alembic migrations, если не требуется hard reset истории;
- Prometheus/Grafana/Streamlit как оболочку, но с новым текстом и новыми метриками.

Причина: эти компоненты обслуживают любую текстовую ML-классификацию и не содержат обязательной зависимости от prompt safety или sentiment taxonomy.

## 5. Где Живет SecurePrompt Guard

### Код

Удалить или полностью заменить:

- `app/infrastructure/ml/prompt_guard/classifier.py`;
- `app/infrastructure/ml/prompt_guard/rules.py`;
- `app/infrastructure/ml/hf_prompt_guard/__init__.py`;
- `app/infrastructure/ml/hf_prompt_guard/plugin.py`.

Удалить entry из:

- `config/models.yml`: `models.prompt_guard`;
- runtime catalog sync expectations;
- acceptance/demo payloads.

### API Examples И Скрипты

Заменить примеры:

- `app/schemas/classifications.py`: examples сейчас используют `prompt_guard`;
- `README.md`: demo flow отправляет `prompt_guard`;
- `scripts/acceptance_scenario.py`: основной сценарий проверяет `prompt_injection`;
- `scripts/evaluate_classifier.py` может остаться generic, но examples/tests должны перейти на новый model code.

### Тесты

Переписать или удалить тесты, которые ожидают `prompt_guard`, `SecurePrompt Guard`, `prompt_injection`, `jailbreak`, `harmful`, `data_exfiltration`, `suspicious`:

- `tests/unit/test_baseline_classifiers.py`;
- `tests/unit/test_hf_model_plugins.py`;
- `tests/unit/test_model_registry.py`;
- `tests/unit/test_model_config_loader.py`;
- `tests/unit/test_models_api_catalog.py`;
- `tests/unit/test_api_routes.py`;
- `tests/unit/test_worker_task.py`;
- `tests/unit/test_ml_scripts.py`;
- `tests/unit/test_classification_api.py`;
- `tests/unit/test_classification_batch_api.py`;
- `tests/unit/test_classification_batch_service.py`;
- `tests/unit/test_classification_cache.py`;
- `tests/unit/test_classification_models.py`;
- `tests/unit/test_classification_service.py`;
- `tests/unit/test_admin_api.py`;
- `tests/integration/test_model_catalog_sync.py`;
- `tests/integration/test_model_catalog_api_flow.py`;
- `tests/integration/test_model_catalog_repository.py`;
- `tests/integration/test_classification_worker.py`;
- `tests/integration/test_classification_repository.py`;
- `tests/integration/test_classification_batch_repository.py`;
- `tests/integration/test_classification_batch_items_repository.py`;
- `tests/integration/test_classification_cache_worker.py`;
- `tests/integration/test_analytics_repository.py`;
- `tests/integration/test_persisted_metrics.py`;
- `tests/integration/test_maintenance_tasks.py`.

Не все эти тесты нужно удалять. Большая часть проверяет платформу, поэтому правильнее заменить fixtures и ожидаемые labels на новый продуктовый classifier.

### Документация

Обновить:

- `README.md`;
- `docs/FINAL_ARCHITECTURE_REPORT.md`;
- `docs/analysis/requirements_analysis.md`;
- `docs/architecture/system_architecture.md`;
- `docs/architecture/technology_decisions.md`;
- `docs/architecture/tradeoffs.md`;
- `docs/ml/dataset_cards.md`;
- `docs/ml/ml_strategy.md`;
- `docs/research/datasets_research.md`;
- `docs/research/ml_models_research.md`;
- `docs/TECHNICAL_TASK.MD`;
- `docs/TECHNICAL_TASK_IMPROVEMENTS.md`.

`docs/superpowers/plans/*` и `docs/superpowers/specs/*` содержат много исторических упоминаний. Для продуктовой чистоты лучше либо перенести их в `docs/archive/`, либо добавить явное пояснение, что это historical implementation artifacts и они не описывают актуальный продукт.

## 6. Где Живет Старая TextMood Логика

Текущий `TextMood Analytics` реализован как классификация:

- `positive`;
- `neutral`;
- `negative`;
- `angry`;
- `urgent`;
- `toxic`.

По задаче эту продуктовую ось нужно убрать, включая тональность, срочность, злость и токсичность.

### Код

Заменить:

- `app/infrastructure/ml/text_mood/classifier.py`;
- `app/infrastructure/ml/hf_sentiment/__init__.py`;
- `app/infrastructure/ml/hf_sentiment/plugin.py`.

Обновить:

- `config/models.yml`: labels, task_type, model_class, supported modes, pricing;
- `README.md`: описание TextMood;
- `scripts/acceptance_scenario.py`: сценарий с `text_mood`;
- tests, перечисленные выше.

### Документация И ML Research

Удалить/переписать research по:

- SST-2;
- TweetEval/CardiffNLP sentiment;
- GoEmotions/DAIR anger;
- Jigsaw Toxic Comment;
- urgency dataset.

Эти материалы больше не должны быть recommended path для актуального продукта.

## 7. Рекомендуемое Новое Позиционирование

Чтобы сохранить название `TextMood Analytics`, но убрать forbidden taxonomy, предлагается сузить смысл продукта:

> TextMood Analytics анализирует клиентские сообщения как бизнес-сигналы: о чем пишет клиент, какие сущности и темы встречаются, как это распределяется по каналам и периодам, без оценки эмоционального состояния, токсичности или prompt safety.

Новый product model лучше строить не вокруг "настроения", а вокруг `message intelligence`:

- topic/intent classification;
- key phrase/entity extraction;
- aggregate trends;
- privacy-safe analytics;
- routing hints на основе темы, а не срочности или токсичности.

## 8. Предлагаемые Фичи

### Фича 1: Topic And Intent Analytics

Суть: заменить labels `positive/negative/angry/urgent/toxic` на бизнес-темы и намерения.

Начальный taxonomy:

- `billing_question`;
- `refund_request`;
- `technical_issue`;
- `account_access`;
- `delivery_or_status`;
- `feature_request`;
- `general_question`;
- `other`.

Что дает продукту:

- понятный B2B use case для helpdesk/CRM;
- можно показывать распределение тем, динамику обращений и топ проблем;
- сохраняется существующий pipeline: classifier, model catalog, billing, batch, analytics;
- не используется анализ тональности, злости, срочности или токсичности.

Минимальный MVP:

- новый rule-based classifier `TextIntentClassifier` или `TextMoodTopicClassifier`;
- `model_code`: оставить `text_mood` для совместимости или переименовать в `text_insights`;
- `task_type`: `message_intent_classification`;
- `recommended_action`: `route_billing`, `route_support`, `route_product`, `route_general`;
- обновить `/analytics/by-label` как распределение тем.

### Фича 2: Privacy-Safe Key Insight Extraction

Суть: добавить в результат не эмоциональные оценки, а структурированные business insights:

- `detected_entities`: типы сущностей без хранения raw sensitive values, например `order_id`, `invoice_id`, `account_reference`, `product_name`;
- `keywords`: нормализованные ключевые фразы;
- `redaction_applied`: флаг;
- `summary_hint`: короткое безопасное описание запроса без персональных данных.

Что дает продукту:

- усиливает enterprise-позиционирование;
- делает dashboard полезнее, потому что можно строить аналитику по темам и сущностям;
- снижает риск утечки raw text;
- хорошо сочетается с текущими security notes "не показывать raw prompt/text".

Минимальный MVP:

- добавить metadata в `ClassificationOutput.metadata`;
- расширить dashboard/analytics для entity counts;
- не менять DB schema на первом этапе, потому что metadata уже хранится JSON в `classification_results.metadata`;
- позднее вынести entity analytics в отдельную таблицу, если появятся запросы по большим объемам.

## 9. Рекомендуемый Scope Следующего Этапа

### Этап A: Product Cleanup

1. Переименовать проектные метаданные:
   - `pyproject.toml`: `secure-prompt-guard` -> `text-mood-analytics`;
   - `app/core/config.py`: `UniClassify Platform` -> `TextMood Analytics`;
   - Streamlit titles и README.
2. Удалить `prompt_guard` и `hf_prompt_guard` modules.
3. Удалить `prompt_guard` из `config/models.yml`.
4. Заменить старый `TextMoodClassifier` на новый intent/topic classifier.
5. Удалить `hf_sentiment` или заменить на будущий generic HF text-classification adapter без sentiment naming.
6. Обновить examples в schemas, README, scripts.

### Этап B: Tests Rewrite

1. Сначала переписать unit tests для classifier, model registry, config loader.
2. Затем переписать API tests и worker tests на новый taxonomy.
3. Затем обновить integration tests для repositories/analytics/model catalog.
4. Проверить:

```bash
uv run pytest
uv run pytest --cov=app --cov-fail-under=70
uv run ruff check .
uv run python -m compileall app tests alembic scripts
```

### Этап C: Documentation Rewrite

1. README сделать главным актуальным документом продукта.
2. Старые technical task docs либо переписать, либо перенести в archive.
3. ML strategy и dataset research заменить на topic/intent/entity extraction research.
4. Architecture docs обновить с `Registry --> TextMood Intent Plugin` вместо `Prompt Guard Plugin`/`TextMood Plugin`.

### Этап D: Optional API Naming

Текущие `/api/v1/classifications` можно оставить для минимального риска: это generic classification API.

Если нужен более продуктовый внешний контракт, отдельным этапом добавить alias:

- `POST /api/v1/analyses`;
- `POST /api/v1/analyses/batch`;
- `GET /api/v1/analyses/{request_id}`.

Старые `/classifications` оставить как backward-compatible routes до конца MVP.

## 10. Data И Migration Notes

Схема БД в целом generic. Обязательной schema migration для удаления продуктов нет.

Но если БД уже содержит model catalog rows, нужен один из вариантов:

- для локальной demo-среды: пересоздать БД и прогнать Alembic заново;
- для сохраняемой БД: добавить data migration или maintenance script, который деактивирует `prompt_guard`, обновляет `text_mood` labels/task_type/pricing и чистит устаревшие model pricing rows.

Исторические classification requests с `prompt_guard` можно оставить как audit/history, но UI и API catalog не должны предлагать этот model code для новых запросов.

## 11. Риски

- Простая замена строк недостаточна: tests и docs содержат много доменных ожиданий по labels.
- Удаление `prompt_guard` без обновления `config/models.yml` сломает registry startup.
- Удаление labels без переписывания tests приведет к массовым падениям в worker, API, analytics и model catalog tests.
- Если оставить `hf_sentiment`, продуктовая чистота будет нарушена даже без использования этого plugin в config.
- `docs/superpowers/*` могут создавать ложное впечатление, что SecurePrompt Guard все еще является актуальной целью.
- Переименование `/classifications` в `/analyses` сразу увеличит blast radius. Лучше сначала заменить product logic, затем решать внешний API naming.

## 12. Рекомендуемое Решение

Для следующего этапа выбрать консервативный путь:

1. Сохранить платформенное ядро и endpoint family `/classifications`.
2. Удалить SecurePrompt Guard полностью из активного кода, config, README, demo и тестов.
3. Заменить старый TextMood sentiment/urgency/anger/toxicity classifier на topic/intent classifier.
4. Добавить metadata для privacy-safe insights в рамках существующего `ClassificationOutput.metadata`.
5. Обновить analytics/dashboard так, чтобы `by-label` означал topic distribution.
6. Не менять DB schema без необходимости.

Такой путь минимизирует риск, сохраняет сильные части уже реализованного backend и дает понятный продуктовый фокус для `TextMood Analytics`.
