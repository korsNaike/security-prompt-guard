import time

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.infrastructure.db.session import AsyncSessionLocal
from app.infrastructure.monitoring.metrics import metrics_registry
from app.infrastructure.monitoring.persisted_metrics import render_persisted_prometheus_metrics


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "SecurePrompt Guard API for prompt injection, jailbreak, harmful prompt, "
            "and data exfiltration classification."
        ),
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

    @app.get("/ready", tags=["health"], summary="Service readiness check")
    async def ready() -> dict[str, str]:
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1 FROM users LIMIT 1"))
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="database unavailable",
            ) from exc
        return {"status": "ready", "service": settings.app_name}

    @app.get("/metrics", tags=["monitoring"], summary="Prometheus metrics")
    async def metrics() -> PlainTextResponse:
        rendered = metrics_registry.render_prometheus()
        try:
            async with AsyncSessionLocal() as session:
                rendered += await render_persisted_prometheus_metrics(session)
        except Exception:
            rendered += "# persisted metrics unavailable\n"
        return PlainTextResponse(rendered)

    return app


app = create_app()
