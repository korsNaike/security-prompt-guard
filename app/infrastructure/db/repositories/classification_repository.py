import hashlib
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.classifications.entities import ClassificationStatus
from app.domain.ml.classifier_contracts import ClassificationOutput
from app.infrastructure.db.models import (
    ClassificationBatchItemModel,
    ClassificationBatchModel,
    ClassificationRequestModel,
    ClassificationResultModel,
)


class ClassificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_request(
        self,
        *,
        user_id: UUID,
        model_code: str,
        mode: str,
        input_text: str,
        estimated_cost: int,
        batch_id: UUID | None = None,
    ) -> ClassificationRequestModel:
        request = ClassificationRequestModel(
            user_id=user_id,
            batch_id=batch_id,
            model_code=model_code,
            mode=mode,
            input_text=input_text,
            input_hash=self.calculate_input_hash(input_text),
            estimated_cost=estimated_cost,
            status=ClassificationStatus.PENDING.value,
        )
        self.session.add(request)
        await self.session.flush()
        return request

    async def create_batch(
        self,
        *,
        user_id: UUID,
        total_requests: int,
        estimated_cost: int,
    ) -> ClassificationBatchModel:
        batch = ClassificationBatchModel(
            user_id=user_id,
            total_requests=total_requests,
            estimated_cost=estimated_cost,
            status=ClassificationStatus.PENDING.value,
        )
        self.session.add(batch)
        await self.session.flush()
        return batch

    async def create_batch_item(
        self,
        *,
        batch_id: UUID,
        classification_request_id: UUID,
        item_index: int,
        estimated_cost: int,
    ) -> ClassificationBatchItemModel:
        item = ClassificationBatchItemModel(
            batch_id=batch_id,
            classification_request_id=classification_request_id,
            item_index=item_index,
            estimated_cost=estimated_cost,
            status=ClassificationStatus.PENDING.value,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def get_batch_item_by_request_id(
        self,
        request_id: UUID,
    ) -> ClassificationBatchItemModel | None:
        result = await self.session.execute(
            select(ClassificationBatchItemModel).where(
                ClassificationBatchItemModel.classification_request_id == request_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, request_id: UUID) -> ClassificationRequestModel | None:
        result = await self.session.execute(
            select(ClassificationRequestModel)
            .options(selectinload(ClassificationRequestModel.result))
            .where(ClassificationRequestModel.id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_user(
        self,
        *,
        request_id: UUID,
        user_id: UUID,
    ) -> ClassificationRequestModel | None:
        result = await self.session.execute(
            select(ClassificationRequestModel)
            .options(selectinload(ClassificationRequestModel.result))
            .where(
                ClassificationRequestModel.id == request_id,
                ClassificationRequestModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        limit: int = 50,
    ) -> list[ClassificationRequestModel]:
        result = await self.session.execute(
            select(ClassificationRequestModel)
            .options(selectinload(ClassificationRequestModel.result))
            .where(ClassificationRequestModel.user_id == user_id)
            .order_by(ClassificationRequestModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_all(self, *, limit: int = 100) -> list[ClassificationRequestModel]:
        result = await self.session.execute(
            select(ClassificationRequestModel)
            .options(selectinload(ClassificationRequestModel.result))
            .order_by(ClassificationRequestModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_batch_for_user(
        self,
        *,
        batch_id: UUID,
        user_id: UUID,
    ) -> ClassificationBatchModel | None:
        result = await self.session.execute(
            select(ClassificationBatchModel)
            .options(selectinload(ClassificationBatchModel.requests))
            .where(
                ClassificationBatchModel.id == batch_id,
                ClassificationBatchModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_batch_progress(self, batch_id: UUID) -> ClassificationBatchModel | None:
        result = await self.session.execute(
            select(ClassificationBatchModel)
            .options(selectinload(ClassificationBatchModel.requests))
            .where(ClassificationBatchModel.id == batch_id)
        )
        batch = result.scalar_one_or_none()
        if batch is None:
            return None

        completed = sum(
            1
            for request in batch.requests
            if request.status == ClassificationStatus.COMPLETED.value
        )
        failed = sum(
            1 for request in batch.requests if request.status == ClassificationStatus.FAILED.value
        )
        batch.completed_requests = completed
        batch.failed_requests = failed
        batch.final_cost = sum(request.final_cost or 0 for request in batch.requests)

        finished = completed + failed
        if finished < batch.total_requests:
            batch.status = ClassificationStatus.PROCESSING.value if finished else batch.status
        elif failed == 0:
            batch.status = ClassificationStatus.COMPLETED.value
            batch.completed_at = datetime.now(UTC)
        elif completed == 0:
            batch.status = ClassificationStatus.FAILED.value
            batch.completed_at = datetime.now(UTC)
        else:
            batch.status = ClassificationStatus.PARTIAL_SUCCESS.value
            batch.completed_at = datetime.now(UTC)

        await self.session.flush()
        return batch

    async def set_celery_task_id(
        self,
        *,
        request_id: UUID,
        celery_task_id: str,
    ) -> None:
        request = await self.get_by_id(request_id)
        if request is None:
            return
        request.celery_task_id = celery_task_id
        await self.session.flush()

    async def mark_processing(
        self,
        request: ClassificationRequestModel,
    ) -> ClassificationRequestModel:
        request.status = ClassificationStatus.PROCESSING.value
        request.started_at = datetime.now(UTC)
        request.error_message = None
        await self.session.flush()
        return request

    async def mark_batch_item_processing(self, request_id: UUID) -> None:
        item = await self.get_batch_item_by_request_id(request_id)
        if item is not None:
            item.status = ClassificationStatus.PROCESSING.value
            await self.session.flush()

    async def mark_batch_item_completed(
        self,
        request_id: UUID,
        final_cost: int | None = None,
    ) -> None:
        item = await self.get_batch_item_by_request_id(request_id)
        if item is not None:
            item.status = ClassificationStatus.COMPLETED.value
            item.final_cost = final_cost
            item.completed_at = datetime.now(UTC)
            item.error_message = None
            await self.session.flush()

    async def mark_batch_item_failed(self, request_id: UUID, error_message: str) -> None:
        item = await self.get_batch_item_by_request_id(request_id)
        if item is not None:
            item.status = ClassificationStatus.FAILED.value
            item.completed_at = datetime.now(UTC)
            item.error_message = error_message[:4000]
            await self.session.flush()

    async def save_success(
        self,
        *,
        request: ClassificationRequestModel,
        output: ClassificationOutput,
        model_code: str,
        model_version: str,
        final_cost: int,
    ) -> ClassificationResultModel:
        request.status = ClassificationStatus.COMPLETED.value
        request.final_cost = final_cost
        request.completed_at = datetime.now(UTC)
        request.error_message = None

        result = ClassificationResultModel(
            request_id=request.id,
            label=output.label,
            confidence=output.confidence,
            risk_level=output.risk_level,
            recommended_action=output.recommended_action,
            explanation=output.explanation,
            raw_scores=output.raw_scores,
            result_metadata=output.metadata,
            model_code=model_code,
            model_version=model_version,
        )
        self.session.add(result)
        await self.session.flush()
        request.result = result
        return result

    async def mark_failed(
        self,
        *,
        request: ClassificationRequestModel,
        error_message: str,
    ) -> ClassificationRequestModel:
        request.status = ClassificationStatus.FAILED.value
        request.completed_at = datetime.now(UTC)
        request.error_message = error_message[:4000]
        await self.session.flush()
        return request

    async def mark_stale_processing_failed(self, *, older_than: datetime) -> int:
        result = await self.session.execute(
            select(ClassificationRequestModel).where(
                ClassificationRequestModel.status == ClassificationStatus.PROCESSING.value,
                ClassificationRequestModel.started_at < older_than,
            )
        )
        requests = list(result.scalars().all())
        for request in requests:
            request.status = ClassificationStatus.FAILED.value
            request.completed_at = datetime.now(UTC)
            request.error_message = "Classification request expired during processing"
            await self.mark_batch_item_failed(request.id, request.error_message)
        await self.session.flush()
        return len(requests)

    @staticmethod
    def calculate_input_hash(input_text: str) -> str:
        normalized = " ".join(input_text.strip().split()).casefold()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    async def get_user_analytics_summary(self, user_id: UUID) -> dict:
        result = await self.session.execute(
            select(
                func.count(ClassificationRequestModel.id),
                func.coalesce(func.sum(ClassificationRequestModel.estimated_cost), 0),
                func.coalesce(func.sum(ClassificationRequestModel.final_cost), 0),
            ).where(ClassificationRequestModel.user_id == user_id)
        )
        total_requests, total_estimated_cost, total_final_cost = result.one()

        status_result = await self.session.execute(
            select(ClassificationRequestModel.status, func.count(ClassificationRequestModel.id))
            .where(ClassificationRequestModel.user_id == user_id)
            .group_by(ClassificationRequestModel.status)
        )
        status_counts = {status: int(count) for status, count in status_result.all()}

        result_rows = await self.session.execute(
            select(ClassificationResultModel.result_metadata)
            .join(ClassificationRequestModel)
            .where(ClassificationRequestModel.user_id == user_id)
        )
        cache_hits = sum(
            1
            for (metadata,) in result_rows.all()
            if isinstance(metadata, dict) and metadata.get("cache_hit") is True
        )

        return {
            "total_requests": int(total_requests),
            "completed_requests": status_counts.get(ClassificationStatus.COMPLETED.value, 0),
            "failed_requests": status_counts.get(ClassificationStatus.FAILED.value, 0),
            "total_estimated_cost": int(total_estimated_cost or 0),
            "total_final_cost": int(total_final_cost or 0),
            "cache_hits": cache_hits,
        }

    async def get_user_usage_breakdown(self, user_id: UUID) -> list[dict]:
        result = await self.session.execute(
            select(ClassificationRequestModel.status, func.count(ClassificationRequestModel.id))
            .where(ClassificationRequestModel.user_id == user_id)
            .group_by(ClassificationRequestModel.status)
            .order_by(ClassificationRequestModel.status)
        )
        return [{"status": status, "count": int(count)} for status, count in result.all()]

    async def get_user_model_breakdown(self, user_id: UUID) -> list[dict]:
        result = await self.session.execute(
            select(
                ClassificationRequestModel.model_code,
                func.count(ClassificationRequestModel.id),
                func.coalesce(func.sum(ClassificationRequestModel.final_cost), 0),
            )
            .where(ClassificationRequestModel.user_id == user_id)
            .group_by(ClassificationRequestModel.model_code)
            .order_by(ClassificationRequestModel.model_code)
        )
        return [
            {"model_code": model_code, "count": int(count), "final_cost": int(final_cost or 0)}
            for model_code, count, final_cost in result.all()
        ]

    async def get_user_label_breakdown(self, user_id: UUID) -> list[dict]:
        result = await self.session.execute(
            select(
                ClassificationResultModel.label,
                func.count(ClassificationResultModel.id),
            )
            .join(ClassificationRequestModel)
            .where(ClassificationRequestModel.user_id == user_id)
            .group_by(ClassificationResultModel.label)
            .order_by(ClassificationResultModel.label)
        )
        return [{"label": label, "count": int(count)} for label, count in result.all()]
