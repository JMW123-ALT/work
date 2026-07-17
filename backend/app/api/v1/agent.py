"""Agent 和流式问答路由 — 薄路由层。

所有业务逻辑（prompt、检索实现、SSE 拼接）已迁移至：
  - app/agents/common/retrievers.py    (V2Retriever)
  - app/agents/knowledge_qa/agent.py  (KnowledgeQAAgent)
  - app/agents/wenchuang/agent.py     (run_agent)
  - app/common/sse.py                 (sse_event)
"""

from typing import Annotated

from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse

from app.agents.common.retrievers import V2Retriever
from app.agents.knowledge_qa.agent import KnowledgeQAAgent
from app.agents.wenchuang.agent import run_agent
from app.schemas.agent import AgentChatRequest
from app.services.permissions import normalize_user_type

router = APIRouter(tags=["Wenchuang Agent"])


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
    agent = KnowledgeQAAgent(user_type=user_type)
    return StreamingResponse(agent.stream_answer(req), media_type="text/event-stream")
