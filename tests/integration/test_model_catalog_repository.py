import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

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


async def test_upsert_model_catalog_and_pricing(session_factory) -> None:
    async with session_factory() as session:
        repository = ModelCatalogRepository(session)
        await repository.upsert_model(
            model_code="prompt_guard",
            product_name="SecurePrompt Guard",
            model_name="PromptGuardClassifier",
            model_version="0.1.0",
            task_type="prompt_security_classification",
            labels=["safe", "prompt_injection"],
            pricing={"basic": 3, "standard": 7},
        )
        await repository.upsert_model(
            model_code="prompt_guard",
            product_name="SecurePrompt Guard",
            model_name="PromptGuardClassifier",
            model_version="0.1.1",
            task_type="prompt_security_classification",
            labels=["safe", "prompt_injection", "jailbreak"],
            pricing={"basic": 4, "standard": 8},
        )
        await session.commit()

    async with session_factory() as session:
        items = await ModelCatalogRepository(session).list_models()

        assert len(items) == 1
        assert items[0].model_version == "0.1.1"
        assert {price.mode: price.cost for price in items[0].pricing if price.is_active} == {
            "basic": 4,
            "standard": 8,
        }
