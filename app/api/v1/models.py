from fastapi import APIRouter, HTTPException

from app.core.exceptions import ModelNotFoundError
from app.infrastructure.ml.loader import model_registry
from app.schemas.models import ModelInfo, ModelListResponse

router = APIRouter()


def _to_schema(descriptor) -> ModelInfo:
    return ModelInfo(
        model_code=descriptor.model_code,
        product_name=descriptor.product_name,
        model_name=descriptor.model_name,
        version=descriptor.model_version,
        task_type=descriptor.task_type,
        supported_modes=descriptor.supported_modes,
        labels=descriptor.labels,
        pricing=descriptor.pricing,
    )


@router.get("", summary="List available ML models")
async def list_models() -> ModelListResponse:
    return ModelListResponse(items=[_to_schema(item) for item in model_registry.list_models()])


@router.get("/{model_code}", summary="Get model metadata")
async def get_model(model_code: str) -> ModelInfo:
    try:
        return _to_schema(model_registry.describe(model_code))
    except ModelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
