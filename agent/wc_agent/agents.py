"""各个 Agent 节点的业务逻辑。

这些函数会被 `graph.py` 注册到 LangGraph 中。每个节点接收当前
`WenchuangState`，并返回自己要更新的字段。
"""

from __future__ import annotations

import re
from typing import Any

from .llm import UnifiedLLM
from .prompts import load_prompt
from .state import AgentStatus, Intent, WenchuangState


def parse_intent_and_keywords(query: str) -> tuple[Intent, list[str], str]:
    """从用户输入中解析任务类型、关键词和风格。

    当前先用规则实现，便于稳定可控；后续可以换成小模型分类。
    """

    if any(word in query for word in ["策展", "展陈", "展览", "展厅"]):
        intent: Intent = "exhibition"
    elif any(word in query for word in ["文案", "小红书", "抖音", "种草", "脚本", "电商"]):
        intent = "copywriting"
    elif any(word in query for word in ["是什么", "介绍", "讲解", "问答", "科普"]):
        intent = "qa"
    else:
        intent = "ip_design"

    style = "国潮厚重风"
    if any(word in query for word in ["潮玩", "年轻", "可爱", "萌"]):
        style = "潮玩年轻化风"
    elif any(word in query for word in ["极简", "高级", "博物馆风"]):
        style = "极简博物馆风"

    raw_keywords = re.split(r"[，,。；;\s/]+", query)
    stop_words = {"我要", "帮我", "做一个", "生成", "输出"}
    keywords = [item for item in raw_keywords if item and item not in stop_words]
    return intent, keywords[:8] or [query[:20]], style


def intent_node(state: WenchuangState) -> dict[str, Any]:
    """需求解析节点：把原始 query 转成结构化意图。"""

    intent, keywords, style = parse_intent_and_keywords(state.user_query)
    return {"intent": intent, "keywords": keywords, "style": style}


async def cultural_review_node(state: WenchuangState) -> dict[str, Any]:
    """文化考据节点。

    只有在检索到足够证据时才调用 LLM；资料不足时直接返回补充材料提示。
    """

    if state.status == AgentStatus.NEED_MORE_MATERIAL:
        return {
            "cultural_review": "知识库暂无足够高置信度史料，本轮不生成文化结论。请补充史料后重试。",
        }

    llm = UnifiedLLM()
    user = (
        f"用户需求：{state.user_query}\n"
        f"意图：{state.intent}\n"
        f"关键词：{', '.join(state.keywords)}\n"
        f"检索史料：\n{format_evidence(state)}"
    )
    review = await llm.chat(load_prompt("cultural_review"), user, temperature=0.2)
    warnings = list(state.warnings)
    status = state.status
    # LLM 如果主动提示需要人工核验，则把状态升级为人工复核。
    if "需人工核验" in review and status == AgentStatus.OK:
        status = AgentStatus.NEED_HUMAN_REVIEW
        warnings.append("文化考据结果包含需人工核验内容。")
    return {"cultural_review": review, "warnings": warnings, "status": status}


async def design_node(state: WenchuangState) -> dict[str, Any]:
    """创意设计节点：根据考据结果生成产品方案。"""

    if state.status in {AgentStatus.NEED_MORE_MATERIAL, AgentStatus.BLOCKED}:
        return {"design_plan": ""}
    llm = UnifiedLLM()
    user = (
        f"用户需求：{state.user_query}\n"
        f"风格：{state.style}\n"
        f"文化考据：\n{state.cultural_review}\n"
    )
    return {"design_plan": await llm.chat(load_prompt("design"), user, temperature=0.5)}


async def marketing_node(state: WenchuangState) -> dict[str, Any]:
    """营销优化节点：把产品方案转成平台文案。"""

    if state.status in {AgentStatus.NEED_MORE_MATERIAL, AgentStatus.BLOCKED}:
        return {"marketing_copy": ""}
    llm = UnifiedLLM()
    user = (
        f"用户需求：{state.user_query}\n"
        f"文创方案：\n{state.design_plan}\n"
    )
    return {"marketing_copy": await llm.chat(load_prompt("marketing"), user, temperature=0.6)}


def format_evidence(state: WenchuangState) -> str:
    """把 Evidence 列表格式化成可放进 Prompt 的文本。"""

    lines = []
    for idx, item in enumerate(state.evidence, start=1):
        lines.append(
            f"{idx}. 来源：{item.source}；主题：{item.culture_theme}；"
            f"置信度：{item.confidence:.2f}；版权：{item.copyright_status}；风险：{item.risk_level}\n"
            f"{item.text}"
        )
    return "\n\n".join(lines) if lines else "无高置信度史料。"
