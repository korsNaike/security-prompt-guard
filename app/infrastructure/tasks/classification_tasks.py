from uuid import UUID

from app.domain.ml.classifier_contracts import ClassificationInput
from app.infrastructure.db.repositories.billing_repository import BillingRepository
from app.infrastructure.db.repositories.classification_repository import ClassificationRepository
from app.infrastructure.db.session import AsyncSessionLocal
from app.infrastructure.ml.loader import model_registry
from app.infrastructure.tasks.celery_app import celery_app


async def process_classification_request(
    request_id: str,
    *,
    session_factory=AsyncSessionLocal,
    registry=model_registry,
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
        await session.commit()

    try:
        async with session_factory() as session:
            repository = ClassificationRepository(session)
            billing_repository = BillingRepository(session)
            request = await repository.get_by_id(parsed_request_id)
            if request is None:
                return {"request_id": request_id, "status": "not_found"}

            classifier = registry.get(request.model_code)
            output = classifier.predict(
                ClassificationInput(
                    text=request.input_text,
                    model_code=request.model_code,
                    mode=request.mode,
                )
            )

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
                model_code=classifier.model_code,
                model_version=classifier.model_version,
                final_cost=request.estimated_cost,
            )
            await billing_repository.capture_reserved_credits(
                user_id=request.user_id,
                amount=request.estimated_cost,
                idempotency_key=f"classification:{request.id}:capture",
                related_transaction_id=hold.id,
                description=f"Capture classification {request.id}",
                classification_request_id=request.id,
            )
            await session.commit()
            return {
                "request_id": request_id,
                "status": "completed",
                "model_code": classifier.model_code,
                "model_version": classifier.model_version,
                "label": output.label,
                "confidence": output.confidence,
                "risk_level": output.risk_level,
                "recommended_action": output.recommended_action,
                "explanation": output.explanation,
                "raw_scores": output.raw_scores,
                "metadata": output.metadata,
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
                await session.commit()
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

        return anyio.run(process_classification_request, request_id)

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
