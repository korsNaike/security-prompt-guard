from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Universal ML classification service platform.",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["health"], summary="Service health check")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    return app


app = create_app()
