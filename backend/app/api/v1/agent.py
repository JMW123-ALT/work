"""Agent and streaming chat routes."""

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.agent import AgentChatRequest
from app.services.agent import RAGServiceRetriever, run_agent
from app.services.llm_client import llm_client
from app.services.rag_service import rag_service

router = APIRouter(tags=["Wenchuang Agent"])


@router.post("/chat", summary="Wenchuang Agent chat")
async def chat(req: AgentChatRequest):
    """Keep the existing Wenchuang Agent workflow unchanged."""
    retriever = RAGServiceRetriever(
        user_type=req.user_type,
        min_confidence=req.min_confidence,
    )
    return await run_agent(
        req.query,
        retriever=retriever,
        n_results=req.top_k,
        min_confidence=req.min_confidence,
    )


@router.post("/chat/stream", summary="Streaming knowledge-base Q&A")
async def chat_stream(req: AgentChatRequest):
    """Stream a ChatGPT-like answer for the new first tab."""

    async def event_stream() -> AsyncIterator[str]:
        yield _sse("start", {"status": "running"})

        sources = _retrieve_sources(req)
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


def _retrieve_sources(req: AgentChatRequest) -> list[dict]:
    try:
        result = rag_service.search(
            {
                "query": req.query,
                "user_type": req.user_type,
                "top_k": req.top_k,
                "min_confidence": req.min_confidence,
            }
        )
    except Exception:
        return []
    return list(result.get("items") or [])


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
