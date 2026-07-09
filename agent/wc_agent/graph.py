"""LangGraph 主流程编排。

这里只负责把各个节点串起来，并定义异常分支。具体业务逻辑放在
`agents.py`、`guardrails.py` 和 `retrievers.py` 中。
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from .agents import cultural_review_node, design_node, intent_node, marketing_node
from .guardrails import post_guardrails_node, pre_guardrails_node
from .retrievers import Retriever, get_default_retriever
from .state import AgentStatus, WenchuangState


def make_retrieve_node(retriever: Retriever | None = None):
    """创建检索节点。

    允许外部传入不同检索器；未传入时按 `RETRIEVER_PROVIDER` 选择默认实现。
    """

    active_retriever = retriever or get_default_retriever()

    def retrieve_node(state: WenchuangState) -> dict[str, Any]:
        """执行检索，并在无证据时进入资料不足分支。"""

        query = " ".join(state.keywords) or state.user_query
        evidence = active_retriever.search(query)
        if not evidence:
            return {
                "evidence": [],
                "status": AgentStatus.NEED_MORE_MATERIAL,
                "warnings": state.warnings + ["没有检索到高置信度史料，本轮停止生成，等待数据库或补充素材。"],
            }
        return {"evidence": evidence}

    return retrieve_node


def route_after_pre_guardrails(state: WenchuangState) -> str:
    """前置风控后决定是否继续检索。"""

    if state.status == AgentStatus.BLOCKED:
        return "final"
    return "retrieve"


def route_after_retrieve(state: WenchuangState) -> str:
    """检索后决定进入后置风控还是资料不足处理。"""

    if state.status == AgentStatus.NEED_MORE_MATERIAL:
        return "cultural_review"
    return "post_guardrails"


def route_after_cultural_review(state: WenchuangState) -> str:
    """文化考据后决定是否继续设计和营销生成。"""

    if state.status in {AgentStatus.NEED_MORE_MATERIAL, AgentStatus.BLOCKED}:
        return "final"
    return "design"


def final_node(state: WenchuangState) -> dict[str, Any]:
    """最终输出节点，把状态、证据和生成内容汇总成 Markdown。"""

    warnings = "\n".join(f"- {item}" for item in state.warnings) or "- 无"
    evidence = "\n".join(
        f"- {item.culture_theme} | {item.source} | 置信度 {item.confidence:.2f}"
        for item in state.evidence
    ) or "- 无"
    answer = (
        "# 文创 Agent 输出\n\n"
        "## 任务识别\n"
        f"- 意图：{state.intent}\n"
        f"- 关键词：{', '.join(state.keywords)}\n"
        f"- 风格：{state.style}\n"
        f"- 状态：{state.status.value}\n\n"
        f"## 风险/复核提示\n{warnings}\n\n"
        f"## 检索证据\n{evidence}\n\n"
        f"## 文化考据\n{state.cultural_review}\n\n"
        f"## 文创方案\n{state.design_plan}\n\n"
        f"## 营销文案\n{state.marketing_copy}\n"
    )
    return {"final_answer": answer}


def build_graph(retriever: Retriever | None = None):
    """构建并编译 LangGraph 工作流。"""

    graph = StateGraph(WenchuangState)
    graph.add_node("intent", intent_node)
    graph.add_node("pre_guardrails", pre_guardrails_node)
    graph.add_node("retrieve", make_retrieve_node(retriever))
    graph.add_node("post_guardrails", post_guardrails_node)
    graph.add_node("cultural_review", cultural_review_node)
    graph.add_node("design", design_node)
    graph.add_node("marketing", marketing_node)
    graph.add_node("final", final_node)

    graph.add_edge(START, "intent")
    graph.add_edge("intent", "pre_guardrails")
    graph.add_conditional_edges("pre_guardrails", route_after_pre_guardrails, {"retrieve": "retrieve", "final": "final"})
    graph.add_conditional_edges("retrieve", route_after_retrieve, {"post_guardrails": "post_guardrails", "cultural_review": "cultural_review"})
    graph.add_edge("post_guardrails", "cultural_review")
    graph.add_conditional_edges("cultural_review", route_after_cultural_review, {"design": "design", "final": "final"})
    graph.add_edge("design", "marketing")
    graph.add_edge("marketing", "final")
    graph.add_edge("final", END)
    return graph.compile()


async def run_agent(query: str, retriever: Retriever | None = None) -> WenchuangState:
    """运行完整 Agent。

    `retriever` 参数是数据库接入点，测试或真实环境可以在这里注入不同检索器。
    """

    app = build_graph(retriever)
    result = await app.ainvoke(WenchuangState(user_query=query))
    return WenchuangState.model_validate(result)
