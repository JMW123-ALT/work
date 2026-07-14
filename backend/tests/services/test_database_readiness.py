import pytest

from app.services.platform_services.database import DatabaseReadinessService


@pytest.mark.asyncio
async def test_database_readiness_reports_unconfigured_database():
    service = DatabaseReadinessService(database_url="", database_url_sync="")

    result = await service.check()

    assert result["configured"] is False
    assert result["reachable"] is False
    assert result["status"] == "not_configured"
    assert result["alembic_revision"] is None


@pytest.mark.asyncio
async def test_database_readiness_reports_reachable_database():
    async def fake_probe():
        return "005_agent_runtime"

    service = DatabaseReadinessService(
        database_url="postgresql+asyncpg://user:pass@localhost:5432/app",
        database_url_sync="postgresql+psycopg://user:pass@localhost:5432/app",
        probe=fake_probe,
    )

    result = await service.check()

    assert result["configured"] is True
    assert result["reachable"] is True
    assert result["status"] == "ready"
    assert result["alembic_revision"] == "005_agent_runtime"


@pytest.mark.asyncio
async def test_database_readiness_reports_unreachable_database():
    async def fake_probe():
        raise RuntimeError("connection refused")

    service = DatabaseReadinessService(
        database_url="postgresql+asyncpg://user:pass@localhost:5432/app",
        database_url_sync="postgresql+psycopg://user:pass@localhost:5432/app",
        probe=fake_probe,
    )

    result = await service.check()

    assert result["configured"] is True
    assert result["reachable"] is False
    assert result["status"] == "unreachable"
    assert "connection refused" in result["message"]
