import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.infrastructure.db.base import Base
from app.infrastructure.db.repositories.audit_log_repository import AuditLogRepository


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


async def test_audit_log_repository_records_event(session_factory) -> None:
    async with session_factory() as session:
        log = await AuditLogRepository(session).record(
            action="auth.login",
            entity_type="user",
            entity_id="user-1",
            metadata={"email": "user@example.com"},
        )
        await session.commit()

    async with session_factory() as session:
        stored = await session.get(type(log), log.id)

    assert stored.action == "auth.login"
    assert stored.entity_type == "user"
    assert stored.event_metadata == {"email": "user@example.com"}
