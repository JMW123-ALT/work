"""
RAG 搜索路由 — v2 PostgreSQL + Chroma
用统一的 v2 RetrievalService 替换旧 RAGService。
"""
from fastapi import APIRouter, Header, HTTPException, status
from typing import Annotated

from app.db.session import async_session_factory
from app.schemas.rag import SearchRequest, SearchResponse
from app.services.permissions import normalize_user_type
from app.services.platform_services.retrieval import RetrievalService

router = APIRouter(tags=["检索与问答"])


def _require_session():
    if async_session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DATABASE_URL 未配置",
        )


@router.post("/search", response_model=SearchResponse, summary="语义检索 (v2)")
async def search(
    req: SearchRequest,
    x_user_type: Annotated[str | None, Header(alias="X-User-Type")] = None,
):
    _require_session()
    user_type = normalize_user_type(x_user_type or req.user_type)
    payload = req.model_dump()
    payload["user_type"] = user_type
    async with async_session_factory() as session:
        return await RetrievalService(session).search(payload)


@router.post("/ask", summary="RAG 问答 (v2)")
async def ask(
    req: SearchRequest,
    x_user_type: Annotated[str | None, Header(alias="X-User-Type")] = None,
):
    """Simple ask: retrieve then generate answer via LLM."""
    _require_session()
    from app.services.llm_client import llm_client
    from app.services.rag_service import _to_agent_search_item

    user_type = normalize_user_type(x_user_type or req.user_type)
    payload = req.model_dump()
    payload["user_type"] = user_type

    async with async_session_factory() as session:
        result = await RetrievalService(session).search(payload)

    sources = [_to_agent_search_item(item) for item in result.get("items", [])]
    notice = result.get("permissionNotice", "")
    question = req.model_dump().get("query", "")
    llm_result = llm_client.generate_answer(question, sources, notice)
    return {
        **llm_result,
        "sources": sources,
        "blockedCount": result.get("blockedCount", 0),
        "permissionNotice": notice,
        "rerank": result.get("rerank", {}),
    }
