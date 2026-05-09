from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings


async def run_with_isolated_task_session[T](
    callback: Callable[[async_sessionmaker], Awaitable[T]],
) -> T:
    engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        poolclass=NullPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        return await callback(session_factory)
    finally:
        await engine.dispose()
