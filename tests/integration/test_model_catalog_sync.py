import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.infrastructure.db.base import Base
from app.infrastructure.db.repositories.model_catalog_repository import (
    ModelCatalogRepository,
    sync_model_catalog_from_definitions,
)
from app.infrastructure.ml.config_loader import load_model_definitions


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()


async def test_sync_model_catalog_from_default_config(session_factory) -> None:
    definitions = load_model_definitions("config/models.yml")

    async with session_factory() as session:
        repository = ModelCatalogRepository(session)
        await sync_model_catalog_from_definitions(repository, definitions)
        await session.commit()

    async with session_factory() as session:
        items = await ModelCatalogRepository(session).list_models()

        assert {item.model_code for item in items} == {"prompt_guard"}
        assert items[0].model_name == "Rule-Based Prompt Guard Baseline"


async def test_sync_model_catalog_deactivates_models_missing_from_config(session_factory) -> None:
    definitions = load_model_definitions("config/models.yml")

    async with session_factory() as session:
        repository = ModelCatalogRepository(session)
        await repository.upsert_model(
            model_code="retired_model",
            product_name="Retired Model",
            model_name="RetiredClassifier",
            model_version="0.1.0",
            task_type="retired_classification",
            labels=["retired"],
            pricing={"basic": 2},
        )
        await sync_model_catalog_from_definitions(repository, definitions)
        await session.commit()

    async with session_factory() as session:
        repository = ModelCatalogRepository(session)
        items = await repository.list_models()
        stale = await repository.get_model_by_code("retired_model")

        assert {item.model_code for item in items} == {"prompt_guard"}
        assert stale is not None
        assert stale.is_active is False
        assert all(price.is_active is False for price in stale.pricing)
