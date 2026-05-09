from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "secure_prompt_guard",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.infrastructure.tasks.classification_tasks",
        "app.infrastructure.tasks.maintenance_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "monthly-loyalty-recalculation": {
        "task": "maintenance.recalculate_loyalty_tiers",
        "schedule": 60 * 60 * 24 * 30,
    },
    "deactivate-expired-promo-codes": {
        "task": "maintenance.deactivate_expired_promo_codes",
        "schedule": 60 * 60,
    },
    "cleanup-stale-classification-requests": {
        "task": "maintenance.cleanup_stale_classification_requests",
        "schedule": 60 * 15,
    },
}
