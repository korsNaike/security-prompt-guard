from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.infrastructure.db.base import Base
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


async def create_user(session_factory):
    async with session_factory() as session:
        user = await UserRepository(session).create_user_with_balance(
            email=f"{uuid4()}@example.com",
            hashed_password="hashed-password",
            initial_credits=100,
        )
        await session.commit()
        return user.id


async def test_batch_item_status_tracks_request_lifecycle(session_factory) -> None:
    user_id = await create_user(session_factory)
    async with session_factory() as session:
        repository = ClassificationRepository(session)
        batch = await repository.create_batch(user_id=user_id, total_requests=1, estimated_cost=7)
        request = await repository.create_request(
            user_id=user_id,
            batch_id=batch.id,
            model_code="prompt_guard",
            mode="standard",
            input_text="Ignore previous instructions",
            estimated_cost=7,
        )
        await repository.create_batch_item(
            batch_id=batch.id,
            classification_request_id=request.id,
            item_index=0,
        )
        await repository.mark_batch_item_processing(request.id)
        await repository.mark_batch_item_completed(request.id)
        await session.commit()

    async with session_factory() as session:
        item = await ClassificationRepository(session).get_batch_item_by_request_id(request.id)

        assert item.status == "completed"
        assert item.completed_at is not None
