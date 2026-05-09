from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.billing.entities import BillingTransactionStatus, BillingTransactionType
from app.domain.classifications.entities import ClassificationStatus
from app.infrastructure.db.models import (
    BillingTransactionModel,
    ClassificationRequestModel,
    LoyaltyTierHistoryModel,
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


DEFAULT_LOYALTY_TIERS = (
    {
        "code": "bronze",
        "name": "Bronze",
        "min_monthly_predictions": 0,
        "discount_percent": 0,
    },
    {
        "code": "silver",
        "name": "Silver",
        "min_monthly_predictions": 20,
        "discount_percent": 10,
    },
    {
        "code": "gold",
        "name": "Gold",
        "min_monthly_predictions": 100,
        "discount_percent": 20,
    },
)


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

    async def bootstrap_loyalty_tiers(self) -> list[LoyaltyTierModel]:
        result = await self.session.execute(select(LoyaltyTierModel))
        existing_by_code = {tier.code: tier for tier in result.scalars().all()}
        for tier_data in DEFAULT_LOYALTY_TIERS:
            if tier_data["code"] not in existing_by_code:
                self.session.add(LoyaltyTierModel(**tier_data))
        await self.session.flush()

        tiers_result = await self.session.execute(
            select(LoyaltyTierModel)
            .where(LoyaltyTierModel.is_active.is_(True))
            .order_by(LoyaltyTierModel.min_monthly_predictions.desc())
        )
        return list(tiers_result.scalars().all())

    async def recalculate_loyalty_tiers(
        self,
        *,
        period_start: datetime,
        period_end: datetime,
    ) -> int:
        tiers = await self.bootstrap_loyalty_tiers()
        if not tiers:
            return 0

        usage_result = await self.session.execute(
            select(
                ClassificationRequestModel.user_id,
                func.count(ClassificationRequestModel.id),
            )
            .where(
                ClassificationRequestModel.status == ClassificationStatus.COMPLETED.value,
                ClassificationRequestModel.completed_at >= period_start,
                ClassificationRequestModel.completed_at < period_end,
            )
            .group_by(ClassificationRequestModel.user_id)
        )
        usage_by_user = {user_id: int(count) for user_id, count in usage_result.all()}
        if not usage_by_user:
            return 0

        users_result = await self.session.execute(
            select(UserModel).where(UserModel.id.in_(usage_by_user.keys()))
        )
        updated = 0
        for user in users_result.scalars().all():
            predictions_count = usage_by_user[user.id]
            next_tier = next(
                tier
                for tier in tiers
                if predictions_count >= tier.min_monthly_predictions
            )
            if user.loyalty_tier_id == next_tier.id:
                continue
            old_tier_id = user.loyalty_tier_id
            user.loyalty_tier_id = next_tier.id
            user.updated_at = datetime.now(UTC)
            self.session.add(
                LoyaltyTierHistoryModel(
                    user_id=user.id,
                    old_tier_id=old_tier_id,
                    new_tier_id=next_tier.id,
                    period_start=period_start,
                    period_end=period_end,
                    predictions_count=predictions_count,
                )
            )
            updated += 1

        await self.session.flush()
        return updated

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
        classification_request_id: UUID | None = None,
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
            classification_request_id=classification_request_id,
        )

    async def capture_reserved_credits(
        self,
        *,
        user_id: UUID,
        amount: int,
        idempotency_key: str,
        related_transaction_id: UUID,
        description: str,
        classification_request_id: UUID | None = None,
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
            classification_request_id=classification_request_id,
        )

    async def charge_cache_hit(
        self,
        *,
        user_id: UUID,
        amount: int,
        idempotency_key: str,
        related_transaction_id: UUID,
        description: str,
        classification_request_id: UUID | None = None,
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
            transaction_type=BillingTransactionType.CACHE_HIT_CHARGE,
            idempotency_key=idempotency_key,
            description=description,
            related_transaction_id=related_transaction_id,
            classification_request_id=classification_request_id,
        )

    async def refund_reserved_credits(
        self,
        *,
        user_id: UUID,
        amount: int,
        idempotency_key: str,
        related_transaction_id: UUID,
        description: str,
        classification_request_id: UUID | None = None,
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
            classification_request_id=classification_request_id,
        )

    async def get_transaction_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> BillingTransactionModel | None:
        return await self._get_transaction_by_idempotency_key(idempotency_key)

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

    async def create_promo_code(
        self,
        *,
        code: str,
        credits_amount: int,
        max_activations: int | None,
    ) -> PromoCodeModel:
        promo_code = PromoCodeModel(
            code=code.strip().upper(),
            credits_amount=credits_amount,
            max_activations=max_activations,
        )
        self.session.add(promo_code)
        await self.session.flush()
        return promo_code

    async def deactivate_expired_promo_codes(self, *, now: datetime | None = None) -> int:
        current_time = now or datetime.now(UTC)
        result = await self.session.execute(
            select(PromoCodeModel).where(
                PromoCodeModel.is_active.is_(True),
                PromoCodeModel.valid_until.is_not(None),
                PromoCodeModel.valid_until < current_time,
            )
        )
        promo_codes = list(result.scalars().all())
        for promo_code in promo_codes:
            promo_code.is_active = False
        await self.session.flush()
        return len(promo_codes)

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
        classification_request_id: UUID | None = None,
    ) -> BillingTransactionModel:
        transaction = BillingTransactionModel(
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type.value,
            status=BillingTransactionStatus.COMPLETED.value,
            related_transaction_id=related_transaction_id,
            classification_request_id=classification_request_id,
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
