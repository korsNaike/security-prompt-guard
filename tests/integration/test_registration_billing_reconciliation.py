import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.application.auth.use_cases import AuthService
from app.domain.billing.entities import BillingTransactionType
from app.infrastructure.db.base import Base
from app.infrastructure.db.repositories.billing_repository import BillingRepository
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


async def test_register_grants_initial_credits_once(session_factory) -> None:
    async with session_factory() as session:
        service = AuthService(
            repository=UserRepository(session),
            billing_repository=BillingRepository(session),
            initial_credits=100,
        )

        result = await service.register(email="acceptance@example.com", password="password123")
        await session.commit()

    async with session_factory() as session:
        billing = BillingRepository(session)
        balance = await billing.get_balance(result.user.id)
        transactions = await billing.list_transactions(result.user.id)

        assert balance.current_balance == 100
        assert balance.reserved_balance == 0
        assert len(transactions) == 1
        assert transactions[0].transaction_type == BillingTransactionType.INITIAL_GRANT.value
        assert transactions[0].amount == 100
