from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUserDep, DbSessionDep
from app.application.classifications.use_cases import (
    ClassificationBatchNotFoundError,
    ClassificationBatchSizeError,
    ClassificationNotFoundError,
    ClassificationService,
)
from app.core.exceptions import ModelNotFoundError, UnsupportedModeError
from app.domain.classifications.entities import ClassificationStatus
from app.domain.ml.classifier_contracts import ClassificationInput
from app.infrastructure.db.repositories.billing_repository import (
    BillingRepository,
    InsufficientCreditsError,
)
from app.infrastructure.db.repositories.classification_repository import ClassificationRepository
from app.infrastructure.ml.loader import model_registry
from app.infrastructure.tasks.classification_tasks import run_classification_task
from app.schemas.classifications import (
    ClassificationBatchCreateRequest,
    ClassificationBatchCreateResponse,
    ClassificationBatchResponse,
    ClassificationCreateRequest,
    ClassificationCreateResponse,
    ClassificationItemResponse,
    ClassificationListResponse,
    ClassificationResultResponse,
    new_request_id,
)

router = APIRouter()


def enqueue_classification_task(request_id: UUID):
    return run_classification_task.delay(str(request_id))


def get_classification_service(session: DbSessionDep) -> ClassificationService:
    return ClassificationService(
        repository=ClassificationRepository(session),
        billing_repository=BillingRepository(session),
        model_registry=model_registry,
        task_sender=enqueue_classification_task,
    )


ClassificationServiceDep = Annotated[ClassificationService, Depends(get_classification_service)]


def to_result_response(request) -> ClassificationResultResponse:
    result = request.result
    product_name = None
    if result is not None:
        try:
            product_name = model_registry.get(request.model_code).product_name
        except ModelNotFoundError:
            product_name = None
    return ClassificationResultResponse(
        request_id=request.id,
        status=request.status,
        model_code=request.model_code,
        mode=request.mode,
        product_name=product_name,
        label=result.label if result is not None else None,
        risk_level=result.risk_level if result is not None else None,
        confidence=result.confidence if result is not None else None,
        recommended_action=result.recommended_action if result is not None else None,
        explanation=result.explanation if result is not None else None,
        raw_scores=result.raw_scores if result is not None else None,
        metadata=result.result_metadata if result is not None else None,
        cost=request.final_cost,
        estimated_cost=request.estimated_cost,
        final_cost=request.final_cost,
        created_at=request.created_at,
        completed_at=request.completed_at,
        error_message=request.error_message,
    )


def to_item_response(request) -> ClassificationItemResponse:
    return ClassificationItemResponse(
        request_id=request.id,
        status=request.status,
        model_code=request.model_code,
        mode=request.mode,
        estimated_cost=request.estimated_cost,
        final_cost=request.final_cost,
        label=request.result.label if request.result is not None else None,
        created_at=request.created_at,
        completed_at=request.completed_at,
    )


def to_batch_response(batch) -> ClassificationBatchResponse:
    return ClassificationBatchResponse(
        batch_id=batch.id,
        status=batch.status,
        total_requests=batch.total_requests,
        completed_requests=batch.completed_requests,
        failed_requests=batch.failed_requests,
        estimated_cost=batch.estimated_cost,
        final_cost=batch.final_cost,
        request_ids=[request.id for request in batch.requests],
        created_at=batch.created_at,
        completed_at=batch.completed_at,
    )


@router.post("", summary="Create classification request")
async def create_classification(
    payload: ClassificationCreateRequest,
    current_user: CurrentUserDep,
    classification_service: ClassificationServiceDep,
    session: DbSessionDep,
) -> ClassificationCreateResponse:
    try:
        request = await classification_service.create_classification(
            user_id=current_user.id,
            model_code=payload.model_code,
            mode=payload.mode,
            text=payload.text,
        )
        await session.commit()
    except (ModelNotFoundError, UnsupportedModeError) as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except InsufficientCreditsError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc)) from exc

    return ClassificationCreateResponse(
        request_id=request.id,
        status=ClassificationStatus.PENDING.value,
        model_code=request.model_code,
        mode=request.mode,
        estimated_cost=request.estimated_cost,
    )


@router.post("/batch", summary="Create batch classification request")
async def create_classification_batch(
    payload: ClassificationBatchCreateRequest,
    current_user: CurrentUserDep,
    classification_service: ClassificationServiceDep,
    session: DbSessionDep,
) -> ClassificationBatchCreateResponse:
    try:
        result = await classification_service.create_batch(
            user_id=current_user.id,
            model_code=payload.model_code,
            mode=payload.mode,
            items=payload.items,
        )
        await session.commit()
    except (ModelNotFoundError, UnsupportedModeError, ClassificationBatchSizeError) as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except InsufficientCreditsError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc)) from exc

    batch = result["batch"]
    requests = result["requests"]
    return ClassificationBatchCreateResponse(
        batch_id=batch.id,
        status=batch.status,
        total_requests=batch.total_requests,
        estimated_cost=batch.estimated_cost,
        request_ids=[request.id for request in requests],
    )


@router.get("/batch/{batch_id}", summary="Get classification batch")
async def get_classification_batch(
    batch_id: UUID,
    current_user: CurrentUserDep,
    classification_service: ClassificationServiceDep,
) -> ClassificationBatchResponse:
    try:
        batch = await classification_service.get_batch(user_id=current_user.id, batch_id=batch_id)
    except ClassificationBatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return to_batch_response(batch)


@router.get("", summary="List classification requests")
async def list_classifications(
    current_user: CurrentUserDep,
    classification_service: ClassificationServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ClassificationListResponse:
    items = await classification_service.list_classifications(
        user_id=current_user.id,
        limit=limit,
    )
    return ClassificationListResponse(items=[to_item_response(item) for item in items])


@router.post("/sync-preview", summary="Run local synchronous preview classifier")
async def sync_preview(payload: ClassificationCreateRequest) -> ClassificationResultResponse:
    try:
        classifier = model_registry.get(payload.model_code)
        cost = model_registry.get_cost(payload.model_code, payload.mode)
    except (ModelNotFoundError, UnsupportedModeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    output = classifier.predict(
        ClassificationInput(text=payload.text, model_code=payload.model_code, mode=payload.mode)
    )
    return ClassificationResultResponse(
        request_id=new_request_id(),
        status="completed",
        model_code=payload.model_code,
        mode=payload.mode,
        product_name=classifier.product_name,
        label=output.label,
        risk_level=output.risk_level,
        confidence=output.confidence,
        recommended_action=output.recommended_action,
        explanation=output.explanation,
        cost=cost,
    )


@router.get("/{request_id}", summary="Get classification result")
async def get_classification(
    request_id: UUID,
    current_user: CurrentUserDep,
    classification_service: ClassificationServiceDep,
) -> ClassificationResultResponse:
    try:
        request = await classification_service.get_classification(
            user_id=current_user.id,
            request_id=request_id,
        )
    except ClassificationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return to_result_response(request)
