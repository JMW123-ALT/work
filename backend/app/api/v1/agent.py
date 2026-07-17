"""Agent and streaming chat routes — v2 retriever."""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse

from app.core.logging import logger
from app.db.session import async_session_factory
from app.schemas.agent import AgentChatRequest
from app.services.agent import Evidence, run_agent
from app.services.llm_client import llm_client
from app.services.permissions import normalize_user_type
from app.services.rag_service import _to_agent_search_item

router = APIRouter(tags=["Wenchuang Agent"])


class V2Retriever:
    """Adapts RetrievalService to the Agent's Retriever protocol.

    Reads from PostgreSQL + Chroma v2; applies full permission and
    status filters (only 'ready' documents with correct permission_level).
    Agent receives plain Evidence objects — no direct PostgreSQL/Chroma access.
    """

    def __init__(self, user_type: str = "visitor", min_confidence: float = 0.0) -> None:
        self.user_type = user_type
        self.min_confidence = min_confidence

    def search(self, query: str, n_results: int = 5) -> list[dict]:
        if async_session_factory is None:
            logger.warning("V2Retriever: DATABASE_URL not configured, returning empty evidence")
            return []
        import asyncio

        async def _search():
            from app.services.platform_services.retrieval import RetrievalService
            async with async_session_factory() as session:
                result = await RetrievalService(session).search(
                    {
                        "query": query,
                        "user_type": self.user_type,
                        "top_k": n_results,
                        "min_confidence": 0.0,  # Agent filters itself
                    }
                )
            return result.get("items", [])

        try:
            return asyncio.get_event_loop().run_until_complete(_search())
        except RuntimeError:
            # Running inside an existing event loop (e.g. uvicorn)
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, _search())
                return future.result(timeout=30)


@router.post("/chat", summary="Wenchuang Agent chat (v2 knowledge base)")
async def chat(
    req: AgentChatRequest,
    x_user_type: Annotated[str | None, Header(alias="X-User-Type")] = None,
):
    user_type = normalize_user_type(x_user_type or req.user_type or "visitor")
    retriever = V2Retriever(user_type=user_type, min_confidence=req.min_confidence)
    return await run_agent(
        req.query,
        retriever=retriever,
        n_results=req.top_k,
        min_confidence=req.min_confidence,
    )


@router.post("/chat/stream", summary="Streaming knowledge-base Q&A (v2 knowledge base)")
async def chat_stream(
    req: AgentChatRequest,
    x_user_type: Annotated[str | None, Header(alias="X-User-Type")] = None,
):
    user_type = normalize_user_type(x_user_type or req.user_type or "visitor")

    async def event_stream() -> AsyncIterator[str]:
        yield _sse("start", {"status": "running"})

        sources = await _retrieve_sources_v2(req, user_type)
        messages = _build_stream_messages(req, sources)
        answer_parts: list[str] = []

        for chunk in llm_client.stream_chat(messages, temperature=0.3, max_tokens=1800):
            answer_parts.append(chunk)
            yield _sse("delta", {"content": chunk})
            await asyncio.sleep(0)

        final_answer = "".join(answer_parts).strip()
        yield _sse(
            "final",
            {
                "status": "ok",
                "workflow": "chat_stream",
                "intent": "qa",
                "evidence_count": len(sources),
                "final_answer": final_answer,
            },
        )
        yield _sse("done", {"status": "done"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


async def _retrieve_sources_v2(req: AgentChatRequest, user_type: str) -> list[dict]:
    if async_session_factory is None:
        return []
    try:
        from app.services.platform_services.retrieval import RetrievalService
        async with async_session_factory() as session:
            result = await RetrievalService(session).search(
                {
                    "query": req.query,
                    "user_type": user_type,
                    "top_k": req.top_k,
                    "min_confidence": req.min_confidence,
                }
            )
        return [_to_agent_search_item(item) for item in result.get("items", [])]
    except Exception as exc:
        logger.warning("_retrieve_sources_v2 failed: %s", exc)
        return []


def _build_stream_messages(req: AgentChatRequest, sources: list[dict]) -> list[dict[str, str]]:
    system_prompt = (
        "You are a tourism and cultural-creative knowledge-base assistant. "
        "Prefer retrieved knowledge-base context when it is available. "
        "If no context is retrieved, answer directly from general knowledge instead of refusing. "
        "Do not show the retrieval list, and do not invent source citations. "
        "Answer naturally and clearly in Chinese, and keep the conversation easy to continue."
    )

    if sources:
        context = _format_sources_for_prompt(sources)
        system_prompt += f"\n\nRetrieved knowledge-base context:\n{context}"
    else:
        system_prompt += "\n\nNo knowledge-base context was retrieved for this turn. Answer directly."

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for item in req.history[-10:]:
        messages.append({"role": item.role, "content": item.content})
    messages.append({"role": "user", "content": req.query})
    return messages


def _format_sources_for_prompt(sources: list[dict], limit: int = 5) -> str:
    parts = []
    for index, item in enumerate(sources[:limit], 1):
        title = item.get("culture_theme") or item.get("title") or item.get("source") or f"source {index}"
        text = item.get("text") or item.get("content") or item.get("snippet") or ""
        parts.append(f"[{index}] {title}\n{text}")
    return "\n\n".join(parts)
