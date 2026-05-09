from uuid import UUID, uuid4

from app.infrastructure.db.repositories.billing_repository import BillingRepository


class BillingService:
    def __init__(self, repository: BillingRepository) -> None:
        self.repository = repository

    async def get_balance(self, user_id: UUID) -> dict:
        balance = await self.repository.get_balance(user_id)
        return {
            "current_balance": balance.current_balance,
            "reserved_balance": balance.reserved_balance,
        }

    async def list_transactions(self, user_id: UUID) -> list[dict]:
        transactions = await self.repository.list_transactions(user_id)
        return [self._transaction_to_dict(transaction) for transaction in transactions]

    async def top_up(self, user_id: UUID, amount: int, idempotency_key: str | None) -> dict:
        transaction = await self.repository.top_up(
            user_id=user_id,
            amount=amount,
            idempotency_key=idempotency_key or f"top-up:{user_id}:{uuid4()}",
            description="Mock top-up",
        )
        return self._transaction_to_dict(transaction)

    async def activate_promo_code(self, user_id: UUID, code: str) -> dict:
        transaction = await self.repository.activate_promo_code(user_id=user_id, code=code)
        return self._transaction_to_dict(transaction)

    async def get_loyalty_tier(self, user_id: UUID) -> dict:
        tier = await self.repository.get_loyalty_tier(user_id)
        if tier is None:
            return {
                "code": "bronze",
                "name": "Bronze",
                "discount_percent": 0,
                "min_monthly_predictions": 0,
            }
        return {
            "code": tier.code,
            "name": tier.name,
            "discount_percent": tier.discount_percent,
            "min_monthly_predictions": tier.min_monthly_predictions,
        }

    def _transaction_to_dict(self, transaction) -> dict:
        return {
            "id": transaction.id,
            "amount": transaction.amount,
            "transaction_type": transaction.transaction_type,
            "status": transaction.status,
            "description": transaction.description,
            "created_at": transaction.created_at,
        }
