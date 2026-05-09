from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.billing.entities import BillingTransactionType
from app.domain.ml.classifier_contracts import ClassificationOutput
from app.infrastructure.db.base import Base
from app.infrastructure.db.repositories.billing_repository import BillingRepository
from app.infrastructure.db.repositories.classification_repository import ClassificationRepository
from app.infrastructure.db.repositories.user_repository import UserRepository


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


async def test_analytics_aggregates_are_user_scoped(session_factory) -> None:
    async with session_factory() as session:
        user = await UserRepository(session).create_user_with_balance(
            email=f"{uuid4()}@example.com",
            hashed_password="hashed",
            initial_credits=0,
        )
        other = await UserRepository(session).create_user_with_balance(
            email=f"{uuid4()}@example.com",
            hashed_password="hashed",
            initial_credits=0,
        )
        repository = ClassificationRepository(session)
        request = await repository.create_request(
            user_id=user.id,
            model_code="prompt_guard",
            mode="standard",
            input_text="hello",
            estimated_cost=7,
        )
        await repository.save_success(
            request=request,
            output=ClassificationOutput(
                label="safe",
                confidence=0.9,
                risk_level="low",
                recommended_action="allow",
                explanation="ok",
                raw_scores={},
                metadata={"cache_hit": True},
            ),
            model_code="prompt_guard",
            model_version="1.0.0",
            final_cost=1,
        )
        request.completed_at = datetime.now(UTC)
        other_request = await repository.create_request(
            user_id=other.id,
            model_code="prompt_guard",
            mode="standard",
            input_text="other",
            estimated_cost=7,
        )
        await repository.save_success(
            request=other_request,
            output=ClassificationOutput(
                label="safe",
                confidence=0.9,
                risk_level="low",
                recommended_action="allow",
                explanation="ok",
                raw_scores={},
                metadata={},
            ),
            model_code="prompt_guard",
            model_version="1.0.0",
            final_cost=7,
        )
        await BillingRepository(session)._create_transaction(
            user_id=user.id,
            amount=-1,
            transaction_type=BillingTransactionType.CACHE_HIT_CHARGE,
            idempotency_key=f"cache:{request.id}",
            description="cache",
            classification_request_id=request.id,
        )
        await session.commit()

    async with session_factory() as session:
        classification_repository = ClassificationRepository(session)
        billing_repository = BillingRepository(session)
        summary = await classification_repository.get_user_analytics_summary(user.id)
        usage = await classification_repository.get_user_usage_breakdown(user.id)
        models = await classification_repository.get_user_model_breakdown(user.id)
        costs = await billing_repository.get_user_cost_breakdown(user.id)

    assert summary == {
        "total_requests": 1,
        "completed_requests": 1,
        "failed_requests": 0,
        "total_estimated_cost": 7,
        "total_final_cost": 1,
        "cache_hits": 1,
    }
    assert usage == [{"status": "completed", "count": 1}]
    assert models == [{"model_code": "prompt_guard", "count": 1, "final_cost": 1}]
    assert costs == [{"transaction_type": "cache_hit_charge", "amount": -1, "count": 1}]
