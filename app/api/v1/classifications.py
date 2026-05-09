from fastapi import APIRouter, HTTPException

from app.core.exceptions import ModelNotFoundError, UnsupportedModeError
from app.domain.ml.classifier_contracts import ClassificationInput
from app.infrastructure.ml.loader import model_registry
from app.schemas.classifications import (
    ClassificationCreateRequest,
    ClassificationCreateResponse,
    ClassificationResultResponse,
    new_request_id,
)

router = APIRouter()


@router.post("", summary="Create classification request")
async def create_classification(
    payload: ClassificationCreateRequest,
) -> ClassificationCreateResponse:
    try:
        estimated_cost = model_registry.get_cost(payload.model_code, payload.mode)
    except (ModelNotFoundError, UnsupportedModeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ClassificationCreateResponse(
        request_id=new_request_id(),
        status="pending",
        model_code=payload.model_code,
        mode=payload.mode,
        estimated_cost=estimated_cost,
    )


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
        product_name=classifier.product_name,
        label=output.label,
        risk_level=output.risk_level,
        confidence=output.confidence,
        recommended_action=output.recommended_action,
        explanation=output.explanation,
        cost=cost,
    )
