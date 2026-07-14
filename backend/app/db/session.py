from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


def create_async_engine_from_settings():
    if not settings.database_url:
        return None
    return create_async_engine(settings.database_url, pool_pre_ping=True)


async_engine = create_async_engine_from_settings()

async_session_factory = (
    async_sessionmaker(async_engine, expire_on_commit=False)
    if async_engine is not None
    else None
)


async def get_async_session() -> AsyncIterator[AsyncSession]:
    if async_session_factory is None:
        raise RuntimeError("DATABASE_URL is not configured")
    async with async_session_factory() as session:
        yield session
