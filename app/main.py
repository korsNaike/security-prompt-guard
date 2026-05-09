import time

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.infrastructure.monitoring.metrics import metrics_registry


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Universal ML classification service platform.",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    @app.middleware("http")
    async def metrics_middleware(request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        metrics_registry.record_http(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_seconds=duration,
        )
        return response

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["health"], summary="Service health check")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    @app.get("/metrics", tags=["monitoring"], summary="Prometheus metrics")
    async def metrics() -> PlainTextResponse:
        return PlainTextResponse(metrics_registry.render_prometheus())

    return app


app = create_app()
