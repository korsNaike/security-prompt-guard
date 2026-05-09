from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "uniclassify",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.infrastructure.tasks.classification_tasks"],
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
