from datetime import UTC, datetime, timedelta

import anyio

from app.infrastructure.db.repositories.billing_repository import BillingRepository
from app.infrastructure.db.repositories.classification_repository import ClassificationRepository
from app.infrastructure.db.session import AsyncSessionLocal
from app.infrastructure.tasks.celery_app import celery_app


def current_month_window(now: datetime) -> tuple[datetime, datetime]:
    current = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
    period_start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if period_start.month == 12:
        period_end = period_start.replace(year=period_start.year + 1, month=1)
    else:
        period_end = period_start.replace(month=period_start.month + 1)
    return period_start, period_end


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


async def recalculate_loyalty_tiers_once(
    *,
    session_factory=AsyncSessionLocal,
    now: datetime | None = None,
) -> dict:
    async with session_factory() as session:
        period_start, period_end = current_month_window(now or datetime.now(UTC))
        updated = await BillingRepository(session).recalculate_loyalty_tiers(
            period_start=period_start,
            period_end=period_end,
        )
        await session.commit()
        return {
            "updated": updated,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
        }


@celery_app.task(name="maintenance.deactivate_expired_promo_codes")
def deactivate_expired_promo_codes_task() -> dict:
    return anyio.run(deactivate_expired_promo_codes_once)


@celery_app.task(name="maintenance.cleanup_stale_classification_requests")
def cleanup_stale_classification_requests_task() -> dict:
    return anyio.run(cleanup_stale_classification_requests_once)


@celery_app.task(name="maintenance.recalculate_loyalty_tiers")
def recalculate_loyalty_tiers_task() -> dict:
    return anyio.run(recalculate_loyalty_tiers_once)
