from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.billing.entities import BillingTransactionStatus, BillingTransactionType
from app.infrastructure.db.models import (
    BillingTransactionModel,
    LoyaltyTierModel,
    PromoCodeActivationModel,
    PromoCodeModel,
    UserBalanceModel,
    UserModel,
)


class InsufficientCreditsError(Exception):
    pass


class BalanceNotFoundError(Exception):
    pass


class PromoCodeInvalidError(Exception):
    pass


class PromoCodeAlreadyActivatedError(Exception):
    pass


class BillingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_balance(self, user_id: UUID) -> UserBalanceModel:
        return await self._get_balance_for_update(user_id)

    async def list_transactions(
        self,
        user_id: UUID,
        limit: int = 50,
    ) -> list[BillingTransactionModel]:
        result = await self.session.execute(
            select(BillingTransactionModel)
            .where(BillingTransactionModel.user_id == user_id)
            .order_by(BillingTransactionModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_loyalty_tier(self, user_id: UUID) -> LoyaltyTierModel | None:
        result = await self.session.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalar_one_or_none()
        if user is None or user.loyalty_tier_id is None:
            return None
        tier_result = await self.session.execute(
            select(LoyaltyTierModel).where(LoyaltyTierModel.id == user.loyalty_tier_id)
        )
        return tier_result.scalar_one_or_none()

    async def create_initial_grant(self, *, user_id: UUID, amount: int) -> BillingTransactionModel:
        return await self._add_positive_balance_transaction(
            user_id=user_id,
            amount=amount,
            transaction_type=BillingTransactionType.INITIAL_GRANT,
            idempotency_key=f"user:{user_id}:initial_grant",
            description="Initial registration credits",
        )

    async def top_up(
        self,
        *,
        user_id: UUID,
        amount: int,
        idempotency_key: str,
        description: str,
    ) -> BillingTransactionModel:
        return await self._add_positive_balance_transaction(
            user_id=user_id,
            amount=amount,
            transaction_type=BillingTransactionType.TOP_UP,
            idempotency_key=idempotency_key,
            description=description,
        )

    async def reserve_credits(
        self,
        *,
        user_id: UUID,
        amount: int,
        idempotency_key: str,
        description: str,
    ) -> BillingTransactionModel:
        existing = await self._get_transaction_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing
        if amount <= 0:
            raise ValueError("amount must be positive")

        balance = await self._get_balance_for_update(user_id)
        if balance.current_balance < amount:
            raise InsufficientCreditsError("Insufficient credits")
        balance.current_balance -= amount
        balance.reserved_balance += amount
        balance.updated_at = datetime.now(UTC)

        return await self._create_transaction(
            user_id=user_id,
            amount=-amount,
            transaction_type=BillingTransactionType.INFERENCE_HOLD,
            idempotency_key=idempotency_key,
            description=description,
        )

    async def capture_reserved_credits(
        self,
        *,
        user_id: UUID,
        amount: int,
        idempotency_key: str,
        related_transaction_id: UUID,
        description: str,
    ) -> BillingTransactionModel:
        existing = await self._get_transaction_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing
        if amount <= 0:
            raise ValueError("amount must be positive")

        balance = await self._get_balance_for_update(user_id)
        if balance.reserved_balance < amount:
            raise InsufficientCreditsError("Insufficient reserved credits")
        balance.reserved_balance -= amount
        balance.updated_at = datetime.now(UTC)

        return await self._create_transaction(
            user_id=user_id,
            amount=-amount,
            transaction_type=BillingTransactionType.INFERENCE_CAPTURE,
            idempotency_key=idempotency_key,
            description=description,
            related_transaction_id=related_transaction_id,
        )

    async def refund_reserved_credits(
        self,
        *,
        user_id: UUID,
        amount: int,
        idempotency_key: str,
        related_transaction_id: UUID,
        description: str,
    ) -> BillingTransactionModel:
        existing = await self._get_transaction_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing
        if amount <= 0:
            raise ValueError("amount must be positive")

        balance = await self._get_balance_for_update(user_id)
        if balance.reserved_balance < amount:
            raise InsufficientCreditsError("Insufficient reserved credits")
        balance.reserved_balance -= amount
        balance.current_balance += amount
        balance.updated_at = datetime.now(UTC)

        return await self._create_transaction(
            user_id=user_id,
            amount=amount,
            transaction_type=BillingTransactionType.INFERENCE_REFUND,
            idempotency_key=idempotency_key,
            description=description,
            related_transaction_id=related_transaction_id,
        )

    async def activate_promo_code(self, *, user_id: UUID, code: str) -> BillingTransactionModel:
        normalized_code = code.strip().upper()
        promo_code = await self._get_promo_code_for_update(normalized_code)
        if promo_code is None or not promo_code.is_active:
            raise PromoCodeInvalidError("Promo code is not active")
        if (
            promo_code.valid_until is not None
            and self._as_aware(promo_code.valid_until) < datetime.now(UTC)
        ):
            raise PromoCodeInvalidError("Promo code has expired")
        if (
            promo_code.max_activations is not None
            and promo_code.used_count >= promo_code.max_activations
        ):
            raise PromoCodeInvalidError("Promo code activation limit reached")

        existing_activation = await self._get_promo_activation(
            promo_code_id=promo_code.id,
            user_id=user_id,
        )
        if existing_activation is not None:
            raise PromoCodeAlreadyActivatedError("Promo code already activated by user")

        promo_code.used_count += 1
        activation = PromoCodeActivationModel(
            promo_code_id=promo_code.id,
            user_id=user_id,
            credits_granted=promo_code.credits_amount,
        )
        self.session.add(activation)

        return await self._add_positive_balance_transaction(
            user_id=user_id,
            amount=promo_code.credits_amount,
            transaction_type=BillingTransactionType.PROMO_GRANT,
            idempotency_key=f"promo:{promo_code.id}:user:{user_id}",
            description=f"Promo code {promo_code.code}",
        )

    async def _add_positive_balance_transaction(
        self,
        *,
        user_id: UUID,
        amount: int,
        transaction_type: BillingTransactionType,
        idempotency_key: str,
        description: str,
    ) -> BillingTransactionModel:
        existing = await self._get_transaction_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing
        if amount <= 0:
            raise ValueError("amount must be positive")

        balance = await self._get_balance_for_update(user_id)
        balance.current_balance += amount
        balance.updated_at = datetime.now(UTC)
        return await self._create_transaction(
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type,
            idempotency_key=idempotency_key,
            description=description,
        )

    async def _get_balance_for_update(self, user_id: UUID) -> UserBalanceModel:
        statement = select(UserBalanceModel).where(UserBalanceModel.user_id == user_id)
        if self.session.bind is not None and self.session.bind.dialect.name != "sqlite":
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        balance = result.scalar_one_or_none()
        if balance is None:
            raise BalanceNotFoundError("User balance was not found")
        return balance

    async def _get_promo_code_for_update(self, code: str) -> PromoCodeModel | None:
        statement = select(PromoCodeModel).where(PromoCodeModel.code == code)
        if self.session.bind is not None and self.session.bind.dialect.name != "sqlite":
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def _get_promo_activation(
        self,
        *,
        promo_code_id: UUID,
        user_id: UUID,
    ) -> PromoCodeActivationModel | None:
        result = await self.session.execute(
            select(PromoCodeActivationModel).where(
                PromoCodeActivationModel.promo_code_id == promo_code_id,
                PromoCodeActivationModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_transaction_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> BillingTransactionModel | None:
        result = await self.session.execute(
            select(BillingTransactionModel).where(
                BillingTransactionModel.idempotency_key == idempotency_key
            )
        )
        return result.scalar_one_or_none()

    async def _create_transaction(
        self,
        *,
        user_id: UUID,
        amount: int,
        transaction_type: BillingTransactionType,
        idempotency_key: str,
        description: str | None,
        related_transaction_id: UUID | None = None,
    ) -> BillingTransactionModel:
        transaction = BillingTransactionModel(
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type.value,
            status=BillingTransactionStatus.COMPLETED.value,
            related_transaction_id=related_transaction_id,
            idempotency_key=idempotency_key,
            description=description,
        )
        self.session.add(transaction)
        await self.session.flush()
        return transaction

    def _as_aware(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
