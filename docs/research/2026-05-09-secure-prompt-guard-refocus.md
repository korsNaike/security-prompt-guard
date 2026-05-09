# SecurePrompt Guard Refocus Research

Дата: 2026-05-09

## Цель

Подготовить проект к фокусировке на одном продукте: SecurePrompt Guard. Следующий этап должен удалить TextMood Analytics и все, что связано с анализом тональности, срочности, злости и токсичности текста, не ломая универсальное ядро классификации, биллинга, очередей, аналитики и мониторинга.

## Статус Форка

Форк создан как локальный git clone:

- исходник: `/Users/grinev.kv/PycharmProjects/unik/itmo/ml-services/secure-prompt-guard`
- рабочий форк: `/Users/grinev.kv/PycharmProjects/unik/itmo/ml-services/secure-prompt-guard-fork`
- ветка: `main`
- `origin`: локальный исходный репозиторий

## Архитектурная Карта

Проект является FastAPI backend-сервисом для платной асинхронной классификации текста:

- API: `app/api/v1/*`
- application/use cases: `app/application/*`
- domain contracts: `app/domain/*`
- infrastructure: SQLAlchemy repositories, Celery, Redis cache, ML plugins, metrics
- model catalog: `config/models.yml` + `app/infrastructure/ml/config_loader.py` + `app/infrastructure/db/repositories/model_catalog_repository.py`
- tests: `tests/unit`, `tests/integration`

Ключевой вывод: большая часть системы уже не привязана к TextMood. `ClassificationService`, Celery worker, billing, cache, analytics и DB-модели работают через `model_code`, `mode`, `label`, `risk_level` и `recommended_action`. Поэтому удаление TextMood должно быть в основном конфигурационным, тестовым и документационным, плюс точечная зачистка ML-плагинов.

## Точки Привязки TextMood

### Runtime И Конфигурация

Обязательные изменения:

- `config/models.yml`
  - удалить модель `text_mood`;
  - оставить только `prompt_guard`;
  - проверить, что `labels` больше не содержат `positive`, `neutral`, `negative`, `angry`, `urgent`, `toxic`.
- `app/infrastructure/ml/text_mood/classifier.py`
  - удалить файл и директорию `app/infrastructure/ml/text_mood/`.
- `app/infrastructure/ml/hf_sentiment/__init__.py`
- `app/infrastructure/ml/hf_sentiment/plugin.py`
  - удалить HuggingFace sentiment plugin, так как он относится к анализу тональности.
- `pyproject.toml`
  - заменить описание проекта, где сейчас упоминается `text mood analytics`;
  - зависимость `transformers` можно оставить, если сохраняется `hf_prompt_guard`; удалять ее только если отдельно отказываемся от HuggingFace prompt guard plugin.

Низкий риск:

- `app/infrastructure/ml/loader.py` динамически строит registry из `config/models.yml`, hardcode `text_mood` отсутствует.
- `app/domain/ml/model_registry.py` универсален, менять не нужно.
- `app/domain/ml/classifier_contracts.py` универсален, менять не нужно.
- `app/application/classifications/use_cases.py` универсален, менять не нужно.
- `app/infrastructure/tasks/classification_tasks.py` универсален, менять не нужно.
- `app/api/v1/classifications.py` универсален, менять не нужно.
- `app/api/v1/models.py` универсален, менять не нужно.
- `app/api/v1/analytics.py` универсален, менять не нужно.

### DB И Model Catalog

Важный риск: `sync_model_catalog_from_definitions()` сейчас делает upsert моделей из `config/models.yml`, но не деактивирует модели, которых больше нет в конфиге. Если в БД уже есть `text_mood`, он может остаться активным в `ml_models`, даже после удаления из конфига.

На следующем этапе нужно выбрать один из вариантов:

1. Добавить в `ModelCatalogRepository` метод деактивации моделей, отсутствующих в текущих definitions, и вызвать его из `sync_model_catalog_from_definitions()`.
2. Добавить отдельную Alembic migration, которая выставит `is_active=false` для `ml_models.model_code='text_mood'` и связанных `model_pricing`.

Рекомендация: сделать оба слоя. Runtime sync должен поддерживать конфиг как источник правды, а migration нужна для уже развернутых окружений.

Обратная совместимость с `text_mood` не требуется. Следующий этап может деактивировать каталог модели и не поддерживать чтение старых `text_mood` результатов как отдельный compatibility contract.

### Acceptance И Scripts

Обязательные изменения:

- `scripts/acceptance_scenario.py`
  - заменить batch-сценарий с `model_code="text_mood"` на batch по `prompt_guard`;
  - использовать тексты, которые дают разные prompt safety labels: safe, prompt_injection, data_exfiltration или harmful.

Необязательные изменения:

- `scripts/streamlit_dashboard.py` не содержит TextMood-specific logic. Менять только если будет ребрендинг UniClassify в SecurePrompt Guard.

### Tests

Тесты, которые нужно обновить или удалить:

- `tests/unit/test_baseline_classifiers.py`
  - удалить импорт и тест `TextMoodClassifier`;
  - оставить/расширить проверки `PromptGuardClassifier`.
- `tests/unit/test_model_registry.py`
  - ожидать только `{"prompt_guard"}`;
  - заменить проверки `text_mood` на проверки неподдерживаемого режима `prompt_guard`.
- `tests/unit/test_api_routes.py`
  - `/api/v1/models` должен возвращать только `prompt_guard`;
  - unauthenticated classification request должен использовать `prompt_guard`, а не `text_mood`.
- `tests/unit/test_admin_api.py`
  - admin model catalog должен ожидать только `prompt_guard`.
- `tests/unit/test_hf_model_plugins.py`
  - удалить sentiment factory test, оставить prompt guard HF plugin test.
- `tests/integration/test_model_catalog_sync.py`
  - ожидать только `prompt_guard`;
  - добавить проверку деактивации отсутствующей модели, если будет реализован catalog cleanup.
- `tests/integration/test_classification_repository.py`
  - заменить synthetic `text_mood` rows на `prompt_guard`, если тест не проверяет разные модели как отдельную бизнес-логику.
- `tests/unit/test_transformers_text_classifier.py`
  - файл тестирует общий adapter, но сейчас примеры используют `task_type="sentiment"`. Лучше заменить fixture на prompt-safety labels, чтобы убрать sentiment wording.

### Документация

Документы с упоминаниями TextMood/sentiment/tone/urgency/anger/toxicity:

- `README.md`
- `docs/FINAL_ARCHITECTURE_REPORT.md`
- `docs/analysis/requirements_analysis.md`
- `docs/architecture/system_architecture.md`
- `docs/architecture/tradeoffs.md`
- `docs/ml/dataset_cards.md`
- `docs/ml/ml_strategy.md`
- `docs/research/datasets_research.md`
- `docs/research/ml_models_research.md`
- `docs/TECHNICAL_TASK_IMPROVEMENTS.md`
- `docs/TECHNICAL_TASK.MD`
- `docs/superpowers/plans/*`

Рекомендация по документации:

- активные docs и README переписать под SecurePrompt Guard only;
- исторические superpowers plans можно оставить как архивные артефакты, если не требуется буквальное удаление из истории документации;
- если требование "везде" трактуется строго для рабочей директории, нужно массово зачистить даже исторические plans и `TECHNICAL_TASK.MD`. Это большой шумный diff, но он достижим.

## Рекомендуемая Стратегия Удаления

Подход: сохранить generic classification platform, удалить только TextMood как продукт и sentiment-specific assets.

Шаги следующего этапа:

1. Обновить `config/models.yml`, оставив только `prompt_guard`.
2. Удалить `app/infrastructure/ml/text_mood/` и `app/infrastructure/ml/hf_sentiment/`.
3. Обновить model catalog sync так, чтобы отсутствующие в config модели деактивировались.
4. Добавить Alembic migration для деактивации `text_mood` в существующих БД.
5. Обновить acceptance scenario на prompt guard batch.
6. Обновить тесты registry/API/catalog/classifier/HF plugin.
7. Переписать README и активную архитектурную/ML-документацию.
8. Запустить `uv run pytest`, `uv run ruff check .`, `uv run python -m compileall app tests alembic scripts`.

## Продуктовые Фичи Для Усиления SecurePrompt Guard

### Фича 1: Policy Profiles

Сейчас classifier возвращает label, risk level и recommended action, но action жестко задан в коде. Для продукта безопасности полезнее дать пользователю управляемые политики.

Идея:

- добавить policy profile: `monitor`, `balanced`, `strict`;
- профиль определяет, что делать с `suspicious`, `harmful`, `prompt_injection`, `jailbreak`, `data_exfiltration`;
- API request может принимать `policy_profile`, а default хранится в конфиге;
- ответ содержит `policy_decision`: `allow`, `review`, `block`, `redact`, `step_up_auth`;
- billing и async flow остаются прежними.

Почему это усиливает продукт:

- SecurePrompt Guard становится не просто classifier, а decision engine;
- легче показать enterprise value: разные команды могут выбирать разный уровень блокировок;
- фича хорошо ложится на текущие `risk_level` и `recommended_action`.

Минимальный MVP:

- enum профилей в коде или `config/policies.yml`;
- resolver `label + risk_level + profile -> action`;
- тесты на матрицу решений.

### Фича 2: Evidence And Redaction Hints

Сейчас explanation человекочитаемый, но не структурный. Для security продукта полезно возвращать доказательства срабатывания и подсказки по безопасной обработке текста.

Идея:

- classifier возвращает `evidence`: список найденных паттернов/категорий без раскрытия лишнего контента;
- для credential/data exfiltration добавлять `redaction_hints`: тип секрета, диапазон или нормализованный маркер;
- response metadata показывает, почему сработало правило, и как downstream-система может замаскировать опасный фрагмент.

Почему это усиливает продукт:

- разработчику проще объяснить блокировку пользователю и аудитору;
- можно строить dashboard по типам атак, а не только по labels;
- это расширяет SecurePrompt Guard без добавления второго ML-продукта.

Минимальный MVP:

- расширить rule engine, чтобы он возвращал matched category и safe pattern id;
- сохранить данные в `ClassificationOutput.metadata`;
- добавить тесты, что raw secrets не попадают в evidence.

## Принятые Решения Перед Реализацией

1. Исторические docs и старые implementation plans можно не очищать от TextMood references.
2. Полный runtime-ребрендинг в SecurePrompt Guard входит в scope: `settings.app_name`, Streamlit title, metrics names, Prometheus job и Grafana dashboard.
3. Обратная совместимость для `text_mood` не нужна; модель удаляется из runtime/config, а существующий catalog entry деактивируется.

## Рекомендуемый Следующий План

Сначала выполнить удаление TextMood и стабилизировать тесты. После этого внедрять одну продуктовую фичу. Из двух предложенных фич лучше начать с Policy Profiles: она повышает продуктовую ценность, почти не требует изменения схемы БД и может быть протестирована как чистая бизнес-логика.
