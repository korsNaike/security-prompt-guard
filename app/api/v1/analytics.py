from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUserDep, DbSessionDep
from app.application.analytics.use_cases import AnalyticsService
from app.infrastructure.db.repositories.billing_repository import BillingRepository
from app.infrastructure.db.repositories.classification_repository import ClassificationRepository
from app.schemas.analytics import (
    AnalyticsCostItem,
    AnalyticsCostResponse,
    AnalyticsModelsResponse,
    AnalyticsModelItem,
    AnalyticsSummaryResponse,
    AnalyticsUsageItem,
    AnalyticsUsageResponse,
)

router = APIRouter()


def get_analytics_service(session: DbSessionDep) -> AnalyticsService:
    return AnalyticsService(
        classification_repository=ClassificationRepository(session),
        billing_repository=BillingRepository(session),
    )


AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]


@router.get("/summary", summary="Get analytics summary")
async def analytics_summary(
    current_user: CurrentUserDep,
    service: AnalyticsServiceDep,
) -> AnalyticsSummaryResponse:
    return AnalyticsSummaryResponse(**await service.summary(current_user.id))


@router.get("/usage", summary="Get usage breakdown")
async def analytics_usage(
    current_user: CurrentUserDep,
    service: AnalyticsServiceDep,
) -> AnalyticsUsageResponse:
    return AnalyticsUsageResponse(
        items=[AnalyticsUsageItem(**item) for item in await service.usage(current_user.id)]
    )


@router.get("/costs", summary="Get billing cost breakdown")
async def analytics_costs(
    current_user: CurrentUserDep,
    service: AnalyticsServiceDep,
) -> AnalyticsCostResponse:
    return AnalyticsCostResponse(
        items=[AnalyticsCostItem(**item) for item in await service.costs(current_user.id)]
    )


@router.get("/models", summary="Get model usage breakdown")
async def analytics_models(
    current_user: CurrentUserDep,
    service: AnalyticsServiceDep,
) -> AnalyticsModelsResponse:
    return AnalyticsModelsResponse(
        items=[AnalyticsModelItem(**item) for item in await service.models(current_user.id)]
    )
