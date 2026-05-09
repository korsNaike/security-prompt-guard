from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.classifications.entities import ClassificationStatus
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import ClassificationRequestModel, PromoCodeModel
from app.infrastructure.db.repositories.user_repository import UserRepository
from app.infrastructure.tasks.maintenance_tasks import (
    cleanup_stale_classification_requests_once,
    deactivate_expired_promo_codes_once,
)


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()


async def test_deactivate_expired_promo_codes_is_idempotent(session_factory) -> None:
    async with session_factory() as session:
        session.add(
            PromoCodeModel(
                code="OLD",
                credits_amount=10,
                valid_until=datetime.now(UTC) - timedelta(days=1),
                is_active=True,
            )
        )
        await session.commit()

    first = await deactivate_expired_promo_codes_once(session_factory=session_factory)
    second = await deactivate_expired_promo_codes_once(session_factory=session_factory)

    assert first == {"deactivated": 1}
    assert second == {"deactivated": 0}


async def test_cleanup_stale_processing_requests_marks_failed(session_factory) -> None:
    async with session_factory() as session:
        user = await UserRepository(session).create_user_with_balance(
            email="stale@example.com",
            hashed_password="hashed",
            initial_credits=100,
        )
        request = ClassificationRequestModel(
            user_id=user.id,
            model_code="prompt_guard",
            mode="standard",
            input_text="test",
            input_hash="hash",
            status=ClassificationStatus.PROCESSING.value,
            estimated_cost=7,
            started_at=datetime.now(UTC) - timedelta(hours=2),
        )
        session.add(request)
        await session.commit()

    result = await cleanup_stale_classification_requests_once(session_factory=session_factory)

    assert result == {"failed": 1}
