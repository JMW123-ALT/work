from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


DatabaseProbe = Callable[[], Awaitable[str | None]]


class DatabaseReadinessService:
    """Read-only PostgreSQL readiness check for the platform foundation."""

    def __init__(
        self,
        database_url: str | None = None,
        database_url_sync: str | None = None,
        probe: DatabaseProbe | None = None,
    ) -> None:
        self.database_url = settings.database_url if database_url is None else database_url
        self.database_url_sync = (
            settings.database_url_sync if database_url_sync is None else database_url_sync
        )
        self._probe = probe or self._probe_database

    async def check(self) -> dict[str, Any]:
        if not self.database_url:
            return {
                "configured": False,
                "reachable": False,
                "status": "not_configured",
                "alembic_revision": None,
                "message": "DATABASE_URL is not configured.",
            }

        try:
            revision = await self._probe()
        except Exception as exc:
            return {
                "configured": True,
                "reachable": False,
                "status": "unreachable",
                "alembic_revision": None,
                "message": str(exc),
            }

        return {
            "configured": True,
            "reachable": True,
            "status": "ready" if revision else "no_migration",
            "alembic_revision": revision,
            "message": "Database is reachable."
            if revision
            else "Database is reachable, but Alembic has not been applied.",
        }

    async def _probe_database(self) -> str | None:
        engine = create_async_engine(self.database_url, pool_pre_ping=True)
        try:
            async with engine.connect() as conn:
                await conn.execute(text("select 1"))
                result = await conn.execute(
                    text(
                        "select version_num from alembic_version "
                        "order by version_num desc limit 1"
                    )
                )
                return result.scalar_one_or_none()
        finally:
            await engine.dispose()
