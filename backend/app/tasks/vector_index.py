import asyncio

from app.db.session import async_session_factory
from app.services.platform_services import ChromaIndexService
from app.tasks.celery_app import celery_app


@celery_app.task(name="platform.vector_index_pending")
def vector_index_pending(limit: int = 100) -> dict:
    if async_session_factory is None:
        return {
            "collection": "",
            "indexed": 0,
            "failed": 0,
            "errors": [{"chunk_id": "", "error": "DATABASE_URL is not configured"}],
        }
    return asyncio.run(_run_vector_index(limit))


async def _run_vector_index(limit: int) -> dict:
    async with async_session_factory() as session:
        result = await ChromaIndexService(session).index_pending(limit=limit)
        await session.commit()
        return result
