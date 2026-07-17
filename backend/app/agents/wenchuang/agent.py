"""文创 Agent 入口。

WenchuangAgent 要求调用方显式注入 retriever，
不再静默回退到旧 v1 RAGServiceRetriever。
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from app.agents.common.types import AgentLLM, Retriever
from app.agents.wenchuang.graph import build_graph
from app.agents.wenchuang.state import WenchuangState


class WenchuangAgent:
    """文创策划 Agent（LangGraph 实现）。

    Args:
        retriever: 必须显式传入。V2Retriever 需要请求级 user_type 上下文，
                   无参构造会产生错误生命周期实例；旧 RAGServiceRetriever (v1) 已废弃。
        llm:       可选，默认使用全局 llm_client。
    """

    def __init__(
        self,
        retriever: Retriever,
        llm: AgentLLM | None = None,
    ) -> None:
        if retriever is None:
            raise ValueError(
                "WenchuangAgent requires an explicit retriever. "
                "Pass V2Retriever(user_type=...) from the call site. "
                "RAGServiceRetriever (v1) has been removed."
            )
        self.retriever = retriever
        if llm is None:
            from app.services.llm_client import llm_client
            llm = llm_client
        self.llm = llm

    async def run(
        self,
        user_query: str,
        *,
        n_results: int = 5,
        min_confidence: float = 0.7,
    ) -> dict[str, Any]:
        query = (user_query or "").strip()
        if not query:
            raise ValueError("user_query is required")

        state = WenchuangState(user_query=query)
        graph = build_graph(
            self.retriever,
            self.llm,
            n_results=n_results,
            min_confidence=min_confidence,
        )
        result = await graph.ainvoke({"state": state})
        return result["state"].to_dict()


# ── 便捷函数（供 API 层和测试使用） ───────────────────────────────────────────

async def run_agent(
    user_query: str,
    *,
    retriever: Retriever,
    llm: AgentLLM | None = None,
    n_results: int = 5,
    min_confidence: float = 0.7,
) -> dict[str, Any]:
    """异步运行文创 Agent。retriever 为必填参数。"""
    return await WenchuangAgent(retriever=retriever, llm=llm).run(
        user_query,
        n_results=n_results,
        min_confidence=min_confidence,
    )


def run_agent_sync(
    user_query: str,
    *,
    retriever: Retriever,
    llm: AgentLLM | None = None,
    n_results: int = 5,
    min_confidence: float = 0.7,
) -> dict[str, Any]:
    """同步运行文创 Agent（CLI / 脚本场景）。"""
    return asyncio.run(
        run_agent(
            user_query,
            retriever=retriever,
            llm=llm,
            n_results=n_results,
            min_confidence=min_confidence,
        )
    )


# ── CLI 入口 ─────────────────────────────────────────────────────────────────

async def _main(argv: list[str]) -> int:
    query = " ".join(argv).strip()
    if not query:
        print("Usage: python -m app.agents.wenchuang.agent <user_query>")
        return 2

    import os
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        print(
            "ERROR: DATABASE_URL is not configured. "
            "Set DATABASE_URL to use V2Retriever (PostgreSQL + Chroma v2). "
            "Falling back to RAGServiceRetriever (v1) has been removed."
        )
        return 1

    from app.agents.common.retrievers import V2Retriever
    retriever = V2Retriever(user_type="internal")
    result = await run_agent(query, retriever=retriever)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main(sys.argv[1:])))
