"""跨 Agent 共享检索器。

V2Retriever：基于 PostgreSQL + Chroma v2（RetrievalService），
供文创 Agent 和未来其他 Agent 注入使用。

RAGServiceRetriever（旧 v1 ChromaDB）已于本次重构中删除：
无任何外部消费者（rg 验证），且已被 V2Retriever 完全替代。
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any


class V2Retriever:
    """把 RetrievalService 适配成 Agent 的 Retriever 协议。

    读取 PostgreSQL + Chroma v2；应用完整的权限和状态过滤
    （只返回 status='ready' 且 permission_level 允许的文档）。
    Agent 拿到的是纯 dict 列表，不直接接触 PostgreSQL/Chroma。

    Args:
        user_type:      调用方的用户类型，用于权限过滤。
        min_confidence: 实例级置信度下限（Agent 层自行过滤时传 0.0）。
    """

    def __init__(self, user_type: str = "visitor", min_confidence: float = 0.0) -> None:
        self.user_type = user_type
        self.min_confidence = min_confidence

    def search(self, query: str, n_results: int = 5) -> list[dict[str, Any]]:
        from app.db.session import async_session_factory

        if async_session_factory is None:
            from app.core.logging import logger
            logger.warning("V2Retriever: DATABASE_URL not configured, returning empty evidence")
            return []

        async def _search() -> list[dict[str, Any]]:
            from app.services.platform_services.retrieval import RetrievalService
            async with async_session_factory() as session:
                result = await RetrievalService(session).search(
                    {
                        "query": query,
                        "user_type": self.user_type,
                        "top_k": n_results,
                        "min_confidence": 0.0,  # Agent 自行过滤置信度
                    }
                )
            return result.get("items", [])

        try:
            return asyncio.get_event_loop().run_until_complete(_search())
        except RuntimeError:
            # 已在运行中的事件循环（如 uvicorn）
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, _search())
                return future.result(timeout=30)
