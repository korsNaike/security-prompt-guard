from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.billing.entities import BillingTransactionType
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import PromoCodeModel
from app.infrastructure.db.repositories.billing_repository import (
    BillingRepository,
    InsufficientCreditsError,
    PromoCodeAlreadyActivatedError,
    PromoCodeInvalidError,
)
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
        user_repository = UserRepository(session)
        user = await user_repository.create_user_with_balance(
            email="user@example.com",
            hashed_password="hashed-password",
            initial_credits=100,
        )
        await BillingRepository(session).create_initial_grant(user_id=user.id, amount=100)
        await session.commit()
        return user.id


async def test_top_up_increases_balance_and_is_idempotent(session_factory) -> None:
    user_id = await create_user(session_factory)

    async with session_factory() as session:
        repository = BillingRepository(session)
        first = await repository.top_up(
            user_id=user_id,
            amount=50,
            idempotency_key="top-up:1",
            description="Mock top-up",
        )
        second = await repository.top_up(
            user_id=user_id,
            amount=50,
            idempotency_key="top-up:1",
            description="Mock top-up retry",
        )
        balance = await repository.get_balance(user_id)
        await session.commit()

        assert first.id == second.id
        assert balance.current_balance == 150
        assert balance.reserved_balance == 0


async def test_reserve_capture_and_refund_are_idempotent(session_factory) -> None:
    user_id = await create_user(session_factory)

    async with session_factory() as session:
        repository = BillingRepository(session)
        hold = await repository.reserve_credits(
            user_id=user_id,
            amount=20,
            idempotency_key="classification:req-1:hold",
            description="Reserve inference",
        )
        duplicate_hold = await repository.reserve_credits(
            user_id=user_id,
            amount=20,
            idempotency_key="classification:req-1:hold",
            description="Reserve inference retry",
        )
        balance_after_hold = await repository.get_balance(user_id)
        current_after_hold = balance_after_hold.current_balance
        reserved_after_hold = balance_after_hold.reserved_balance

        capture = await repository.capture_reserved_credits(
            user_id=user_id,
            amount=20,
            idempotency_key="classification:req-1:capture",
            related_transaction_id=hold.id,
            description="Capture inference",
        )
        duplicate_capture = await repository.capture_reserved_credits(
            user_id=user_id,
            amount=20,
            idempotency_key="classification:req-1:capture",
            related_transaction_id=hold.id,
            description="Capture inference retry",
        )
        balance_after_capture = await repository.get_balance(user_id)

        assert hold.id == duplicate_hold.id
        assert capture.id == duplicate_capture.id
        assert current_after_hold == 80
        assert reserved_after_hold == 20
        assert balance_after_capture.current_balance == 80
        assert balance_after_capture.reserved_balance == 0


async def test_reserve_rejects_insufficient_balance(session_factory) -> None:
    user_id = await create_user(session_factory)

    async with session_factory() as session:
        repository = BillingRepository(session)

        with pytest.raises(InsufficientCreditsError):
            await repository.reserve_credits(
                user_id=user_id,
                amount=101,
                idempotency_key="classification:req-2:hold",
                description="Reserve too much",
            )


async def test_refund_restores_reserved_balance(session_factory) -> None:
    user_id = await create_user(session_factory)

    async with session_factory() as session:
        repository = BillingRepository(session)
        hold = await repository.reserve_credits(
            user_id=user_id,
            amount=15,
            idempotency_key="classification:req-3:hold",
            description="Reserve inference",
        )
        await repository.refund_reserved_credits(
            user_id=user_id,
            amount=15,
            idempotency_key="classification:req-3:refund",
            related_transaction_id=hold.id,
            description="Refund failed inference",
        )
        balance = await repository.get_balance(user_id)

        assert balance.current_balance == 100
        assert balance.reserved_balance == 0


async def test_activate_promo_code_grants_credits_once(session_factory) -> None:
    user_id = await create_user(session_factory)

    async with session_factory() as session:
        session.add(PromoCodeModel(code="WELCOME100", credits_amount=100, max_activations=2))
        await session.commit()

    async with session_factory() as session:
        repository = BillingRepository(session)
        transaction = await repository.activate_promo_code(user_id=user_id, code="WELCOME100")
        balance = await repository.get_balance(user_id)

        assert transaction.transaction_type == BillingTransactionType.PROMO_GRANT.value
        assert balance.current_balance == 200

        with pytest.raises(PromoCodeAlreadyActivatedError):
            await repository.activate_promo_code(user_id=user_id, code="WELCOME100")


async def test_activate_promo_code_rejects_expired_code(session_factory) -> None:
    user_id = await create_user(session_factory)

    async with session_factory() as session:
        session.add(
            PromoCodeModel(
                code="OLD",
                credits_amount=100,
                valid_until=datetime.now(UTC) - timedelta(days=1),
            )
        )
        await session.commit()

    async with session_factory() as session:
        repository = BillingRepository(session)

        with pytest.raises(PromoCodeInvalidError):
            await repository.activate_promo_code(user_id=user_id, code="OLD")
