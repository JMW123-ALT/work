"""知识库问答 Agent。

承接 POST /api/v1/chat/stream 的全部业务逻辑，
API 层只负责构造 agent 实例并返回 StreamingResponse。

检索行为与重构前 _retrieve_sources_v2() 完全一致：
  - 使用 RetrievalService（PostgreSQL + Chroma v2）
  - 应用 req.min_confidence 在 RetrievalService 内部过滤
  - 结果经 _to_agent_search_item 映射后传入 prompt
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from app.agents.knowledge_qa.prompts import build_stream_messages
from app.common.sse import sse_event


class KnowledgeQAAgent:
    """知识库流式问答 Agent。

    Args:
        user_type: 调用方的用户类型，用于 RetrievalService 权限过滤。
    """

    def __init__(self, user_type: str = "visitor") -> None:
        self.user_type = user_type

    async def stream_answer(self, req) -> AsyncIterator[str]:
        """流式回答知识库问答请求。

        Args:
            req: AgentChatRequest 对象（query, history, top_k, min_confidence）。

        Yields:
            SSE 格式字符串，依次推送 start / delta / final / done 事件。
        """
        yield sse_event("start", {"status": "running"})

        sources = await self._retrieve_sources(req)
        messages = build_stream_messages(req, sources)
        answer_parts: list[str] = []

        from app.services.llm_client import llm_client
        for chunk in llm_client.stream_chat(messages, temperature=0.3, max_tokens=1800):
            answer_parts.append(chunk)
            yield sse_event("delta", {"content": chunk})
            await asyncio.sleep(0)

        final_answer = "".join(answer_parts).strip()
        yield sse_event(
            "final",
            {
                "status": "ok",
                "workflow": "chat_stream",
                "intent": "qa",
                "evidence_count": len(sources),
                "final_answer": final_answer,
            },
        )
        yield sse_event("done", {"status": "done"})

    async def _retrieve_sources(self, req) -> list[dict]:
        """调用 RetrievalService 检索，行为与原 _retrieve_sources_v2 完全一致。"""
        from app.db.session import async_session_factory

        if async_session_factory is None:
            return []
        try:
            from app.core.logging import logger
            from app.services.platform_services.retrieval import RetrievalService
            from app.services.rag_service import _to_agent_search_item

            async with async_session_factory() as session:
                result = await RetrievalService(session).search(
                    {
                        "query": req.query,
                        "user_type": self.user_type,
                        "top_k": req.top_k,
                        "min_confidence": req.min_confidence,
                    }
                )
            return [_to_agent_search_item(item) for item in result.get("items", [])]
        except Exception as exc:
            from app.core.logging import logger
            logger.warning("KnowledgeQAAgent._retrieve_sources failed: %s", exc)
            return []
