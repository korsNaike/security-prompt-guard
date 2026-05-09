from fastapi import APIRouter

from app.api.v1 import auth, classifications, models

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(
    classifications.router,
    prefix="/classifications",
    tags=["classifications"],
)
