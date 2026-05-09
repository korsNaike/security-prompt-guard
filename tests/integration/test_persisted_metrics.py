import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.ml.classifier_contracts import ClassificationOutput
from app.infrastructure.db.base import Base
from app.infrastructure.db.repositories.classification_repository import ClassificationRepository
from app.infrastructure.db.repositories.user_repository import UserRepository
from app.infrastructure.monitoring.persisted_metrics import render_persisted_prometheus_metrics


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


async def test_persisted_worker_metrics_render_from_db(session_factory) -> None:
    async with session_factory() as session:
        user = await UserRepository(session).create_user_with_balance(
            email="metrics@example.com",
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
        await session.commit()

    async with session_factory() as session:
        rendered = await render_persisted_prometheus_metrics(session)

    assert (
        'uniclassify_worker_outcomes_total{model_code="prompt_guard",'
        'status="completed",cache_hit="true"} 1'
    ) in rendered
    assert (
        'uniclassify_cache_hits_total{model_code="prompt_guard",status="completed"} 1'
    ) in rendered
