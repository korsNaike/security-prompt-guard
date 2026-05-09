from datetime import UTC, datetime, timedelta

import anyio

from app.infrastructure.db.repositories.billing_repository import BillingRepository
from app.infrastructure.db.repositories.classification_repository import ClassificationRepository
from app.infrastructure.db.session import AsyncSessionLocal
from app.infrastructure.tasks.celery_app import celery_app


async def deactivate_expired_promo_codes_once(*, session_factory=AsyncSessionLocal) -> dict:
    async with session_factory() as session:
        count = await BillingRepository(session).deactivate_expired_promo_codes()
        await session.commit()
        return {"deactivated": count}


async def cleanup_stale_classification_requests_once(*, session_factory=AsyncSessionLocal) -> dict:
    async with session_factory() as session:
        older_than = datetime.now(UTC) - timedelta(hours=1)
        count = await ClassificationRepository(session).mark_stale_processing_failed(
            older_than=older_than
        )
        await session.commit()
        return {"failed": count}


async def recalculate_loyalty_tiers_once(*, session_factory=AsyncSessionLocal) -> dict:
    async with session_factory() as session:
        await session.commit()
        return {"updated": 0}


@celery_app.task(name="maintenance.deactivate_expired_promo_codes")
def deactivate_expired_promo_codes_task() -> dict:
    return anyio.run(deactivate_expired_promo_codes_once)


@celery_app.task(name="maintenance.cleanup_stale_classification_requests")
def cleanup_stale_classification_requests_task() -> dict:
    return anyio.run(cleanup_stale_classification_requests_once)


@celery_app.task(name="maintenance.recalculate_loyalty_tiers")
def recalculate_loyalty_tiers_task() -> dict:
    return anyio.run(recalculate_loyalty_tiers_once)
