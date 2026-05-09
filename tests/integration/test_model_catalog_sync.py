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

        assert {item.model_code for item in items} == {"prompt_guard", "text_mood"}
