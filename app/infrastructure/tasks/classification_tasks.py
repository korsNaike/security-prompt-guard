from uuid import UUID

from app.core.config import settings
from app.domain.ml.classifier_contracts import ClassificationInput
from app.infrastructure.cache.classification_cache import (
    CachedClassificationResult,
    classification_cache,
)
from app.infrastructure.db.repositories.billing_repository import BillingRepository
from app.infrastructure.db.repositories.classification_repository import ClassificationRepository
from app.infrastructure.db.session import AsyncSessionLocal
from app.infrastructure.ml.loader import model_registry
from app.infrastructure.monitoring.metrics import metrics_registry
from app.infrastructure.tasks.celery_app import celery_app
from app.infrastructure.tasks.task_session import run_with_isolated_task_session


async def process_classification_request(
    request_id: str,
    *,
    session_factory=AsyncSessionLocal,
    registry=model_registry,
    cache=classification_cache,
) -> dict:
    parsed_request_id = UUID(request_id)

    async with session_factory() as session:
        repository = ClassificationRepository(session)
        request = await repository.get_by_id(parsed_request_id)
        if request is None:
            return {"request_id": request_id, "status": "not_found"}
        if request.status in {"completed", "failed", "cancelled"}:
            return {"request_id": request_id, "status": request.status}
        await repository.mark_processing(request)
        await repository.mark_batch_item_processing(request.id)
        await session.commit()

    try:
        async with session_factory() as session:
            repository = ClassificationRepository(session)
            billing_repository = BillingRepository(session)
            request = await repository.get_by_id(parsed_request_id)
            if request is None:
                return {"request_id": request_id, "status": "not_found"}

            cached_result = cache.get(
                model_code=request.model_code,
                mode=request.mode,
                text=request.input_text,
            )
            cache_hit = cached_result is not None
            if cache_hit:
                output = cached_result.to_output()
                model_code = cached_result.model_code
                model_version = cached_result.model_version
                final_cost = min(settings.cache_hit_cost, request.estimated_cost)
            else:
                classifier = registry.get(request.model_code)
                output = classifier.predict(
                    ClassificationInput(
                        text=request.input_text,
                        model_code=request.model_code,
                        mode=request.mode,
                    )
                )
                model_code = classifier.model_code
                model_version = classifier.model_version
                final_cost = request.estimated_cost

            hold = await billing_repository.get_transaction_by_idempotency_key(
                f"classification:{request.id}:hold"
            )
            if hold is None:
                await repository.mark_failed(
                    request=request,
                    error_message="Reserved billing hold was not found",
                )
                await session.commit()
                return {"request_id": request_id, "status": "failed"}

            await repository.save_success(
                request=request,
                output=output,
                model_code=model_code,
                model_version=model_version,
                final_cost=final_cost,
            )
            await billing_repository.capture_reserved_credits(
                user_id=request.user_id,
                amount=final_cost,
                idempotency_key=f"classification:{request.id}:capture",
                related_transaction_id=hold.id,
                description=f"Capture classification {request.id}",
                classification_request_id=request.id,
            )
            refund_amount = request.estimated_cost - final_cost
            if refund_amount > 0:
                await billing_repository.refund_reserved_credits(
                    user_id=request.user_id,
                    amount=refund_amount,
                    idempotency_key=f"classification:{request.id}:cache-refund",
                    related_transaction_id=hold.id,
                    description=f"Refund cache hit delta for classification {request.id}",
                    classification_request_id=request.id,
                )
            if request.batch_id is not None:
                await repository.mark_batch_item_completed(request.id)
                await repository.update_batch_progress(request.batch_id)
            await session.commit()
            if not cache_hit:
                cache.set(
                    model_code=request.model_code,
                    mode=request.mode,
                    text=request.input_text,
                    result=CachedClassificationResult.from_output(
                        output=output,
                        model_code=model_code,
                        model_version=model_version,
                    ),
                )
            metrics_registry.record_worker(
                model_code=model_code,
                status="completed",
                cache_hit=cache_hit,
            )
            return {
                "request_id": request_id,
                "status": "completed",
                "model_code": model_code,
                "model_version": model_version,
                "label": output.label,
                "confidence": output.confidence,
                "risk_level": output.risk_level,
                "recommended_action": output.recommended_action,
                "explanation": output.explanation,
                "raw_scores": output.raw_scores,
                "metadata": output.metadata,
                "cache_hit": cache_hit,
            }
    except Exception as exc:
        async with session_factory() as session:
            repository = ClassificationRepository(session)
            billing_repository = BillingRepository(session)
            request = await repository.get_by_id(parsed_request_id)
            if request is not None and request.status != "completed":
                hold = await billing_repository.get_transaction_by_idempotency_key(
                    f"classification:{request.id}:hold"
                )
                if hold is not None:
                    await billing_repository.refund_reserved_credits(
                        user_id=request.user_id,
                        amount=request.estimated_cost,
                        idempotency_key=f"classification:{request.id}:refund",
                        related_transaction_id=hold.id,
                        description=f"Refund failed classification {request.id}",
                        classification_request_id=request.id,
                    )
                await repository.mark_failed(request=request, error_message=str(exc))
                if request.batch_id is not None:
                    await repository.mark_batch_item_failed(request.id, str(exc))
                    await repository.update_batch_progress(request.batch_id)
                await session.commit()
                metrics_registry.record_worker(
                    model_code=request.model_code,
                    status="failed",
                    cache_hit=False,
                )
        return {"request_id": request_id, "status": "failed", "error": str(exc)}


@celery_app.task(
    name="classification.run",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def run_classification_task(
    request_id: str,
    model_code: str | None = None,
    mode: str | None = None,
    text: str | None = None,
) -> dict:
    if model_code is None or mode is None or text is None:
        import anyio

        async def run_with_task_session(session_factory):
            return await process_classification_request(
                request_id,
                session_factory=session_factory,
            )

        return anyio.run(run_with_isolated_task_session, run_with_task_session)

    classifier = model_registry.get(model_code)
    output = classifier.predict(ClassificationInput(text=text, model_code=model_code, mode=mode))
    return {
        "request_id": request_id,
        "model_code": model_code,
        "model_version": classifier.model_version,
        "label": output.label,
        "confidence": output.confidence,
        "risk_level": output.risk_level,
        "recommended_action": output.recommended_action,
        "explanation": output.explanation,
        "raw_scores": output.raw_scores,
        "metadata": output.metadata,
    }
