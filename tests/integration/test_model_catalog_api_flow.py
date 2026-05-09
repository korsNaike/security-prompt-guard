import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.application.models.catalog_service import to_model_info
from app.infrastructure.db.base import Base
from app.infrastructure.db.repositories.model_catalog_repository import ModelCatalogRepository


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


async def test_catalog_repository_models_map_to_api_schema(session_factory) -> None:
    async with session_factory() as session:
        repository = ModelCatalogRepository(session)
        await repository.upsert_model(
            model_code="prompt_guard",
            product_name="SecurePrompt Guard",
            model_name="PromptGuardClassifier",
            model_version="0.1.0",
            task_type="prompt_security_classification",
            labels=["safe"],
            pricing={"standard": 7},
        )
        await session.commit()

    async with session_factory() as session:
        model = (await ModelCatalogRepository(session).list_models())[0]
        info = to_model_info(model)

        assert info.model_code == "prompt_guard"
        assert info.pricing == {"standard": 7}
