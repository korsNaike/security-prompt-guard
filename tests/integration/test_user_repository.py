import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.infrastructure.db.base import Base
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


async def test_create_user_with_zero_balance_before_billing_grant(session_factory) -> None:
    async with session_factory() as session:
        repository = UserRepository(session)

        user = await repository.create_user_with_balance(
            email="user@example.com",
            hashed_password="hashed-password",
            initial_credits=100,
        )
        await session.commit()

        assert user.email == "user@example.com"
        assert user.balance.current_balance == 0
        assert user.balance.reserved_balance == 0


async def test_get_user_by_email(session_factory) -> None:
    async with session_factory() as session:
        repository = UserRepository(session)
        await repository.create_user_with_balance(
            email="user@example.com",
            hashed_password="hashed-password",
            initial_credits=100,
        )
        await session.commit()

    async with session_factory() as session:
        repository = UserRepository(session)
        user = await repository.get_by_email("user@example.com")

        assert user is not None
        assert user.email == "user@example.com"


async def test_get_user_by_id(session_factory) -> None:
    async with session_factory() as session:
        repository = UserRepository(session)
        created = await repository.create_user_with_balance(
            email="user@example.com",
            hashed_password="hashed-password",
            initial_credits=100,
        )
        await session.commit()
        user_id = created.id

    async with session_factory() as session:
        repository = UserRepository(session)
        user = await repository.get_by_id(user_id)

        assert user is not None
        assert user.id == user_id
