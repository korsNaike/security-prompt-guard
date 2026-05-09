from uuid import UUID

from app.infrastructure.db.repositories.billing_repository import BillingRepository
from app.infrastructure.db.repositories.classification_repository import ClassificationRepository


class AnalyticsService:
    def __init__(
        self,
        *,
        classification_repository: ClassificationRepository,
        billing_repository: BillingRepository,
    ) -> None:
        self.classification_repository = classification_repository
        self.billing_repository = billing_repository

    async def summary(self, user_id: UUID) -> dict:
        return await self.classification_repository.get_user_analytics_summary(user_id)

    async def usage(self, user_id: UUID) -> list[dict]:
        return await self.classification_repository.get_user_usage_breakdown(user_id)

    async def costs(self, user_id: UUID) -> list[dict]:
        return await self.billing_repository.get_user_cost_breakdown(user_id)

    async def models(self, user_id: UUID) -> list[dict]:
        return await self.classification_repository.get_user_model_breakdown(user_id)

    async def labels(self, user_id: UUID) -> list[dict]:
        return await self.classification_repository.get_user_label_breakdown(user_id)
