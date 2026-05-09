from fastapi import APIRouter

from app.api.v1 import admin, analytics, auth, billing, classifications, models

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(
    classifications.router,
    prefix="/classifications",
    tags=["classifications"],
)
