from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.db.models import MLModelModel, ModelPricingModel


class ModelCatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_models(self) -> list[MLModelModel]:
        result = await self.session.execute(
            select(MLModelModel)
            .options(selectinload(MLModelModel.pricing))
            .where(MLModelModel.is_active.is_(True))
            .order_by(MLModelModel.model_code)
        )
        return list(result.scalars().all())

    async def get_model_by_code(self, model_code: str) -> MLModelModel | None:
        result = await self.session.execute(
            select(MLModelModel)
            .options(selectinload(MLModelModel.pricing))
            .where(MLModelModel.model_code == model_code)
        )
        return result.scalar_one_or_none()

    async def upsert_model(
        self,
        *,
        model_code: str,
        product_name: str,
        model_name: str,
        model_version: str,
        task_type: str,
        labels: list[str],
        pricing: dict[str, int],
    ) -> MLModelModel:
        result = await self.session.execute(
            select(MLModelModel)
            .options(selectinload(MLModelModel.pricing))
            .where(MLModelModel.model_code == model_code)
        )
        model = result.scalar_one_or_none()
        existing = {}
        if model is None:
            model = MLModelModel(
                model_code=model_code,
                product_name=product_name,
                model_name=model_name,
                model_version=model_version,
                task_type=task_type,
                labels=labels,
            )
            self.session.add(model)
            await self.session.flush()
        else:
            existing = {item.mode: item for item in model.pricing}

        model.product_name = product_name
        model.model_name = model_name
        model.model_version = model_version
        model.task_type = task_type
        model.labels = labels
        model.is_active = True

        for mode, cost in pricing.items():
            item = existing.get(mode)
            if item is None:
                item = ModelPricingModel(model_code=model_code, mode=mode, cost=cost)
                self.session.add(item)
            item.cost = cost
            item.is_active = True
        for mode, item in existing.items():
            if mode not in pricing:
                item.is_active = False
        await self.session.flush()
        return model

    async def deactivate_models_except(self, active_model_codes: set[str]) -> None:
        result = await self.session.execute(
            select(MLModelModel).options(selectinload(MLModelModel.pricing))
        )
        for model in result.scalars().all():
            if model.model_code not in active_model_codes:
                model.is_active = False
                for price in model.pricing:
                    price.is_active = False
        await self.session.flush()


async def sync_model_catalog_from_definitions(
    repository: ModelCatalogRepository,
    definitions,
) -> None:
    active_model_codes = {definition.model_code for definition in definitions}
    for definition in definitions:
        await repository.upsert_model(
            model_code=definition.model_code,
            product_name=definition.product_name,
            model_name=definition.model_class.rsplit(".", 1)[-1],
            model_version=definition.version,
            task_type=definition.task_type,
            labels=definition.labels,
            pricing=definition.pricing,
        )
    await repository.deactivate_models_except(active_model_codes)
