from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import ClassificationRequestModel, ClassificationResultModel


async def render_persisted_prometheus_metrics(session: AsyncSession) -> str:
    result = await session.execute(
        select(
            ClassificationRequestModel.model_code,
            ClassificationRequestModel.status,
            ClassificationResultModel.result_metadata,
        ).outerjoin(
            ClassificationResultModel,
            ClassificationResultModel.request_id == ClassificationRequestModel.id,
        )
    )
    worker_outcomes: Counter[tuple[str, str, str]] = Counter()
    cache_hits: Counter[tuple[str, str]] = Counter()
    for model_code, status, metadata in result.all():
        cache_hit = isinstance(metadata, dict) and metadata.get("cache_hit") is True
        cache_hit_label = str(cache_hit).lower()
        worker_outcomes[(model_code, status, cache_hit_label)] += 1
        if cache_hit:
            cache_hits[(model_code, status)] += 1

    lines: list[str] = []
    for (model_code, status, cache_hit), count in sorted(worker_outcomes.items()):
        lines.append(
            "uniclassify_worker_outcomes_total"
            f'{{model_code="{model_code}",status="{status}",cache_hit="{cache_hit}"}} {count}'
        )

    lines.extend(
        [
            "# HELP uniclassify_cache_hits_total Persisted classification cache hits.",
            "# TYPE uniclassify_cache_hits_total counter",
        ]
    )
    for (model_code, status), count in sorted(cache_hits.items()):
        lines.append(
            "uniclassify_cache_hits_total"
            f'{{model_code="{model_code}",status="{status}"}} {count}'
        )

    return "\n".join(lines) + "\n"
