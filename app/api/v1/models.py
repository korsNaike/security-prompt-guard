from fastapi import APIRouter, HTTPException

from app.api.deps import DbSessionDep
from app.application.models.catalog_service import to_model_info
from app.core.config import settings
from app.core.exceptions import ModelNotFoundError
from app.infrastructure.db.repositories.model_catalog_repository import (
    ModelCatalogRepository,
    sync_model_catalog_from_definitions,
)
from app.infrastructure.ml.config_loader import load_model_definitions
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
async def list_models(session: DbSessionDep) -> ModelListResponse:
    try:
        repository = ModelCatalogRepository(session)
        items = await repository.list_models()
        if not items:
            await sync_model_catalog_from_definitions(
                repository,
                load_model_definitions(settings.model_config_path),
            )
            await session.commit()
            items = await repository.list_models()
        return ModelListResponse(items=[to_model_info(item) for item in items])
    except Exception:
        await session.rollback()
    return ModelListResponse(items=[_to_schema(item) for item in model_registry.list_models()])


@router.get("/{model_code}", summary="Get model metadata")
async def get_model(model_code: str) -> ModelInfo:
    try:
        return _to_schema(model_registry.describe(model_code))
    except ModelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
