# System Architecture

## Component View

```mermaid
flowchart TB
    Client[API Client] --> API[FastAPI API]
    API --> Auth[Auth Application Service]
    API --> Billing[Billing Application Service]
    API --> Classify[Classification Application Service]
    API --> Models[Model Catalog Service]
    Classify --> Registry[Model Registry]
    Registry --> PG[Prompt Guard Plugin]
    Registry --> TM[TextMood Plugin]
    Classify --> Queue[Celery Queue]
    Queue --> Worker[Celery Worker]
    Worker --> Registry
    Billing --> DB[(PostgreSQL)]
    Classify --> DB
    API --> Redis[(Redis Cache/Broker)]
    Worker --> DB
    Worker --> Redis
    API --> Metrics[Prometheus Metrics]
    Worker --> Metrics
    Metrics --> Grafana[Grafana]
```

## Layering

```mermaid
flowchart TD
    A[API Layer: FastAPI routers and schemas]
    B[Application Layer: use cases and transaction orchestration]
    C[Domain Layer: entities, service contracts, classifier contracts]
    D[Infrastructure Layer: SQLAlchemy, Redis, Celery, ML plugins, metrics]
    A --> B --> C
    B --> D
    D --> C
```

## Single Classification Sequence

```mermaid
sequenceDiagram
    participant User
    participant API as FastAPI
    participant DB as PostgreSQL
    participant Redis
    participant Worker
    participant Registry
    participant Model as Classifier Plugin

    User->>API: POST /api/v1/classifications
    API->>Registry: validate model_code and mode
    API->>DB: lock balance row and reserve estimated credits
    API->>DB: create classification_request(status=pending)
    API->>Redis: enqueue classification task
    API-->>User: request_id, status=pending
    Worker->>Redis: consume task
    Worker->>DB: set status=processing
    Worker->>Registry: get(model_code)
    Registry-->>Worker: classifier
    Worker->>Model: predict(ClassificationInput)
    Model-->>Worker: ClassificationOutput
    Worker->>DB: save result and capture reserved credits
    Worker->>DB: set status=completed
    User->>API: GET /api/v1/classifications/{request_id}
    API->>DB: read request and result
    API-->>User: completed result
```

## Batch Sequence

```mermaid
sequenceDiagram
    participant User
    participant API
    participant DB
    participant Queue
    participant Worker

    User->>API: POST /classifications/batch
    API->>DB: reserve total estimated cost
    API->>DB: create batch and child requests
    API->>Queue: enqueue each child request
    API-->>User: batch_id, pending
    loop each item
        Worker->>DB: process child request
        alt success
            Worker->>DB: capture item cost
        else failure
            Worker->>DB: refund item reserve
        end
    end
    Worker->>DB: update batch completed/partial_success/failed
```

## Deployment View

```mermaid
flowchart LR
    subgraph Docker Compose
        API[api container]
        W[worker container]
        Beat[beat container]
        PG[(postgres)]
        R[(redis)]
        P[prometheus]
        G[grafana]
        S[streamlit]
    end
    API <--> PG
    API <--> R
    W <--> PG
    W <--> R
    Beat --> R
    P --> API
    P --> W
    G --> P
    S --> API
```

## DB Architecture

- PostgreSQL is the source of truth for users, balances, model catalog, requests, results, transactions, promo codes, loyalty tiers and audit logs.
- Redis is not source of truth. It is broker/cache only.
- Balance mutations must lock `user_balances` with `SELECT ... FOR UPDATE`.
- `billing_transactions.idempotency_key` prevents duplicate hold/capture/refund.

## Caching Architecture

- Cache key: `sha256(model_code + mode + normalized_text + model_version)`.
- Cache hit still creates a request/history row and a `cache_hit_charge` transaction.
- Cache is invalidated naturally by model version changes because version is part of the key.

## Model Registry Architecture

- Registry owns model lookup, model metadata and pricing lookup.
- DB stores model catalog for API visibility and admin controls.
- Runtime registry stores instantiated classifier plugins.
- Future production deployment can move heavy models behind HTTP/gRPC inference adapters while keeping `BaseClassifier`.

## Observability

- API metrics: request count, latency, status codes.
- Worker metrics: tasks processed, task failures, inference duration, retry count.
- Billing metrics: holds, captures, refunds, insufficient balance.
- ML metrics: label distribution, confidence distribution, model version usage.
- Logs should include correlation/request IDs, never raw secrets.

