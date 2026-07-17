"""文创 Agent LangGraph 构图。

_build_graph() 从 WenchuangAgent 中拆出，独立管理图结构，
便于未来替换或扩展节点拓扑。
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.common.types import AgentLLM, Retriever
from app.agents.wenchuang.nodes import (
    cultural_review_node,
    design_node,
    final_node,
    intent_node,
    llm_intent_node,
    marketing_node,
    post_guardrails_node,
    pre_guardrails_node,
    retrieve_node,
)
from app.agents.wenchuang.state import STATUS_BLOCKED, AgentGraphState


def build_graph(
    retriever: Retriever,
    llm: AgentLLM,
    *,
    n_results: int,
    min_confidence: float,
):
    """构建并编译文创 Agent 的 LangGraph 状态图。

    Args:
        retriever:      已注入的检索器实例。
        llm:            已注入的 LLM 实例。
        n_results:      检索返回条数上限。
        min_confidence: 置信度筛选阈值。

    Returns:
        编译后的 CompiledGraph，可直接 ainvoke。
    """
    graph = StateGraph(AgentGraphState)

    # ── 节点包装（绑定 retriever / llm / 参数） ───────────────────────────

    async def intent_step(gs: AgentGraphState) -> AgentGraphState:
        intent_node(gs["state"])
        return gs

    async def pre_guardrails_step(gs: AgentGraphState) -> AgentGraphState:
        pre_guardrails_node(gs["state"])
        return gs

    async def llm_intent_step(gs: AgentGraphState) -> AgentGraphState:
        await llm_intent_node(gs["state"], llm)
        return gs

    async def retrieve_step(gs: AgentGraphState) -> AgentGraphState:
        await retrieve_node(gs["state"], retriever, n_results, min_confidence)
        return gs

    async def post_guardrails_step(gs: AgentGraphState) -> AgentGraphState:
        post_guardrails_node(gs["state"])
        return gs

    async def cultural_review_step(gs: AgentGraphState) -> AgentGraphState:
        await cultural_review_node(gs["state"], llm)
        return gs

    async def design_step(gs: AgentGraphState) -> AgentGraphState:
        await design_node(gs["state"], llm)
        return gs

    async def marketing_step(gs: AgentGraphState) -> AgentGraphState:
        await marketing_node(gs["state"], llm)
        return gs

    async def final_step(gs: AgentGraphState) -> AgentGraphState:
        final_node(gs["state"])
        return gs

    def after_pre_guardrails(gs: AgentGraphState) -> str:
        return "final" if gs["state"].status == STATUS_BLOCKED else "llm_intent"

    # ── 注册节点 ──────────────────────────────────────────────────────────

    graph.add_node("intent", intent_step)
    graph.add_node("pre_guardrails", pre_guardrails_step)
    graph.add_node("llm_intent", llm_intent_step)
    graph.add_node("retrieve", retrieve_step)
    graph.add_node("post_guardrails", post_guardrails_step)
    graph.add_node("cultural_review", cultural_review_step)
    graph.add_node("design", design_step)
    graph.add_node("marketing", marketing_step)
    graph.add_node("final", final_step)

    # ── 边 ────────────────────────────────────────────────────────────────

    graph.set_entry_point("intent")
    graph.add_edge("intent", "pre_guardrails")
    graph.add_conditional_edges(
        "pre_guardrails",
        after_pre_guardrails,
        {"llm_intent": "llm_intent", "final": "final"},
    )
    graph.add_edge("llm_intent", "retrieve")
    graph.add_edge("retrieve", "post_guardrails")
    graph.add_edge("post_guardrails", "cultural_review")
    graph.add_edge("cultural_review", "design")
    graph.add_edge("design", "marketing")
    graph.add_edge("marketing", "final")
    graph.add_edge("final", END)

    return graph.compile()
