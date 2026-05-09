from collections.abc import Callable
from typing import Any
from uuid import UUID

from app.infrastructure.db.repositories.billing_repository import BillingRepository
from app.infrastructure.db.repositories.classification_repository import ClassificationRepository


class ClassificationNotFoundError(Exception):
    pass


class ClassificationBatchNotFoundError(Exception):
    pass


class ClassificationBatchSizeError(Exception):
    pass


class ClassificationService:
    def __init__(
        self,
        *,
        repository: ClassificationRepository,
        billing_repository: BillingRepository,
        model_registry,
        task_sender: Callable[[UUID], Any] | None = None,
    ) -> None:
        self.repository = repository
        self.billing_repository = billing_repository
        self.model_registry = model_registry
        self.task_sender = task_sender

    async def create_classification(
        self,
        *,
        user_id: UUID,
        model_code: str,
        mode: str,
        text: str,
    ):
        estimated_cost = self.model_registry.get_cost(model_code, mode)
        request = await self.repository.create_request(
            user_id=user_id,
            model_code=model_code,
            mode=mode,
            input_text=text,
            estimated_cost=estimated_cost,
        )
        await self.billing_repository.reserve_credits(
            user_id=user_id,
            amount=estimated_cost,
            idempotency_key=self.hold_idempotency_key(request.id),
            description=f"Reserve classification {request.id}",
            classification_request_id=request.id,
        )

        if self.task_sender is not None:
            task = self.task_sender(request.id)
            task_id = getattr(task, "id", None) or (task if isinstance(task, str) else None)
            if task_id is not None:
                await self.repository.set_celery_task_id(
                    request_id=request.id,
                    celery_task_id=str(task_id),
                )
        return request

    async def create_batch(
        self,
        *,
        user_id: UUID,
        model_code: str,
        mode: str,
        texts: list[str],
    ) -> dict:
        if not texts or len(texts) > 50:
            raise ClassificationBatchSizeError("Batch size must be between 1 and 50")

        estimated_cost_per_item = self.model_registry.get_cost(model_code, mode)
        batch = await self.repository.create_batch(
            user_id=user_id,
            total_requests=len(texts),
            estimated_cost=estimated_cost_per_item * len(texts),
        )
        requests = []
        for text in texts:
            request = await self.repository.create_request(
                user_id=user_id,
                batch_id=batch.id,
                model_code=model_code,
                mode=mode,
                input_text=text,
                estimated_cost=estimated_cost_per_item,
            )
            await self.billing_repository.reserve_credits(
                user_id=user_id,
                amount=estimated_cost_per_item,
                idempotency_key=self.hold_idempotency_key(request.id),
                description=f"Reserve classification {request.id}",
                classification_request_id=request.id,
            )
            requests.append(request)

        for request in requests:
            if self.task_sender is not None:
                task = self.task_sender(request.id)
                task_id = getattr(task, "id", None) or (task if isinstance(task, str) else None)
                if task_id is not None:
                    await self.repository.set_celery_task_id(
                        request_id=request.id,
                        celery_task_id=str(task_id),
                    )

        return {"batch": batch, "requests": requests}

    async def get_classification(self, *, user_id: UUID, request_id: UUID):
        request = await self.repository.get_by_id_for_user(request_id=request_id, user_id=user_id)
        if request is None:
            raise ClassificationNotFoundError("Classification request was not found")
        return request

    async def list_classifications(self, *, user_id: UUID, limit: int = 50):
        return await self.repository.list_for_user(user_id=user_id, limit=limit)

    async def get_batch(self, *, user_id: UUID, batch_id: UUID):
        batch = await self.repository.get_batch_for_user(batch_id=batch_id, user_id=user_id)
        if batch is None:
            raise ClassificationBatchNotFoundError("Classification batch was not found")
        return batch

    @staticmethod
    def hold_idempotency_key(request_id: UUID) -> str:
        return f"classification:{request_id}:hold"

    @staticmethod
    def capture_idempotency_key(request_id: UUID) -> str:
        return f"classification:{request_id}:capture"

    @staticmethod
    def refund_idempotency_key(request_id: UUID) -> str:
        return f"classification:{request_id}:refund"
