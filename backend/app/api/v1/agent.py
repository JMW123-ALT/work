"""文创 Agent 路由。"""

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.agent import AgentChatRequest
from app.services.agent import RAGServiceRetriever, run_agent

router = APIRouter(tags=["文创 Agent"])


@router.post("/chat", summary="文创 Agent 对话")
async def chat(req: AgentChatRequest):
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


@router.post("/chat/stream", summary="文创 Agent 流式对话")
async def chat_stream(req: AgentChatRequest):
    async def event_stream() -> AsyncIterator[str]:
        yield _sse("start", {"status": "running"})
        retriever = RAGServiceRetriever(
            user_type=req.user_type,
            min_confidence=req.min_confidence,
        )
        result = await run_agent(
            req.query,
            retriever=retriever,
            n_results=req.top_k,
            min_confidence=req.min_confidence,
        )
        for chunk in _text_chunks(str(result.get("final_answer") or "")):
            yield _sse("delta", {"content": chunk})
        yield _sse("final", result)
        yield _sse("done", {"status": "done"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _text_chunks(text: str, size: int = 160) -> list[str]:
    return [text[index : index + size] for index in range(0, len(text), size)]
