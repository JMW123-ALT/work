"""文创 Agent LangGraph 节点函数。

每个函数直接操作 WenchuangState（就地修改），符合 LangGraph 约定。
"""

from __future__ import annotations

from app.agents.common.types import AgentLLM, Retriever
from app.agents.wenchuang.fallbacks import (
    _fallback_cultural_review,
    _fallback_design_plan,
    _fallback_marketing_copy,
)
from app.agents.wenchuang.guardrails import (
    post_guardrails_node,
    pre_guardrails_node,
)
from app.agents.wenchuang.prompts import (
    CULTURAL_REVIEW_PROMPT_TEMPLATE,
    DESIGN_PROMPT_TEMPLATE,
    LLM_INTENT_PROMPT_TEMPLATE,
    MARKETING_PROMPT_TEMPLATE,
)
from app.agents.wenchuang.state import (
    INTENT_COPYWRITING,
    INTENT_EXHIBITION,
    INTENT_IP_DESIGN,
    INTENT_PLANNING,
    INTENT_QA,
    STATUS_BLOCKED,
    STATUS_NEED_HUMAN_REVIEW,
    STATUS_NEED_MORE_MATERIAL,
    STATUS_OK,
    WenchuangState,
)
from app.agents.wenchuang.utils import (
    _detect_style,
    _extract_keywords,
    _format_evidence_for_prompt,
    _format_warnings,
    _has_any,
    _join_or_default,
    _llm_chat_result,
    _llm_text_or_fallback,
    _maybe_await,
    _json_object,
    _to_evidence,
    _unique,
)


# ── 节点函数 ─────────────────────────────────────────────────────────────────

def intent_node(state: WenchuangState) -> None:
    """基于关键词规则快速判断意图、风格和关键词。"""
    query = state.user_query
    if _has_any(query, ("策展", "展览", "展陈", "展厅")):
        state.intent = INTENT_EXHIBITION
    elif _has_any(query, ("规划", "概念方案", "公园", "景区", "业态", "运营方案")):
        state.intent = INTENT_PLANNING
    elif _has_any(query, ("文案", "小红书", "抖音", "宣传", "种草", "电商")):
        state.intent = INTENT_COPYWRITING
    elif _has_any(query, ("是什么", "介绍", "问答", "解释", "讲解")):
        state.intent = INTENT_QA
    else:
        state.intent = INTENT_IP_DESIGN

    state.style = _detect_style(query)
    state.keywords = _extract_keywords(query)


async def llm_intent_node(state: WenchuangState, llm: AgentLLM) -> None:
    """用 LLM 精化意图、关键词和风格。"""
    prompt = LLM_INTENT_PROMPT_TEMPLATE.format(user_query=state.user_query)
    result = await _llm_chat_result(llm, prompt, temperature=0.1, max_tokens=800)
    state.llm_modes["intent"] = str(result.get("mode") or "unknown")
    parsed = _json_object(str(result.get("content") or ""))
    if not parsed:
        return

    intent = str(parsed.get("intent") or "").strip()
    if intent in {INTENT_IP_DESIGN, INTENT_EXHIBITION, INTENT_COPYWRITING, INTENT_QA, INTENT_PLANNING}:
        state.intent = intent

    keywords = parsed.get("keywords")
    if isinstance(keywords, list):
        cleaned = [str(item).strip() for item in keywords if str(item).strip()]
        if cleaned:
            state.keywords = cleaned

    style = str(parsed.get("style") or "").strip()
    if style:
        state.style = style


async def retrieve_node(
    state: WenchuangState,
    retriever: Retriever,
    n_results: int,
    min_confidence: float,
) -> None:
    """执行 RAG 检索，填充 state.evidence。"""
    search_query = " ".join(state.keywords) if state.keywords else state.user_query
    raw_items = await _maybe_await(retriever.search(search_query, n_results=n_results))
    evidence = [_to_evidence(item) for item in raw_items]
    state.evidence = [item for item in evidence if item.confidence >= min_confidence]

    if not state.evidence:
        if evidence:
            state.evidence = evidence[:n_results]
            state.status = STATUS_NEED_HUMAN_REVIEW
            best_confidence = max(item.confidence for item in state.evidence)
            state.warnings.append(
                "检索到候选资料，但最高置信度 "
                f"{best_confidence:.2f} 低于阈值 {min_confidence:.2f}；"
                "已生成可讨论草案，落地前需人工核验资料相关性。"
            )
            return
        state.status = STATUS_NEED_MORE_MATERIAL
        state.warnings.append(
            f"资料不足：未检索到置信度不低于 {min_confidence:.2f} 的资料，暂不生成方案。"
        )


async def cultural_review_node(state: WenchuangState, llm: AgentLLM) -> None:
    """文化考据节点：基于 evidence 梳理资料依据。"""
    if state.status == STATUS_NEED_MORE_MATERIAL:
        state.cultural_review = "资料不足，无法完成可靠文化考据。"
        return

    prompt = CULTURAL_REVIEW_PROMPT_TEMPLATE.format(
        user_query=state.user_query,
        intent=state.intent,
        warnings=_join_or_default(state.warnings, "无"),
        evidence=_format_evidence_for_prompt(state.evidence),
    )
    state.cultural_review = await _llm_text_or_fallback(
        state,
        "cultural_review",
        llm,
        prompt,
        _fallback_cultural_review(state),
        max_tokens=1200,
    )


async def design_node(state: WenchuangState, llm: AgentLLM) -> None:
    """方案设计节点：基于文化考据输出空间/产品/活动方案。"""
    if state.status in {STATUS_BLOCKED, STATUS_NEED_MORE_MATERIAL}:
        return

    prompt = DESIGN_PROMPT_TEMPLATE.format(
        user_query=state.user_query,
        intent=state.intent,
        style=state.style,
        cultural_review=state.cultural_review,
        evidence=_format_evidence_for_prompt(state.evidence),
    )
    state.design_plan = await _llm_text_or_fallback(
        state,
        "design",
        llm,
        prompt,
        _fallback_design_plan(state),
        max_tokens=1800,
    )


async def marketing_node(state: WenchuangState, llm: AgentLLM) -> None:
    """传播文案节点：基于方案设计输出多平台文案。"""
    if state.status in {STATUS_BLOCKED, STATUS_NEED_MORE_MATERIAL}:
        return

    prompt = MARKETING_PROMPT_TEMPLATE.format(
        user_query=state.user_query,
        design_plan=state.design_plan,
    )
    state.marketing_copy = await _llm_text_or_fallback(
        state,
        "marketing",
        llm,
        prompt,
        _fallback_marketing_copy(state),
        max_tokens=1000,
    )


def final_node(state: WenchuangState) -> None:
    """汇总节点：组装最终输出字符串。"""
    if state.status == STATUS_BLOCKED:
        state.final_answer = "\n".join(
            [
                "最终输出：blocked",
                "该需求命中文化安全高风险规则，已停止生成。",
                *_format_warnings(state.warnings),
            ]
        )
        return

    if state.status == STATUS_NEED_MORE_MATERIAL:
        state.final_answer = "\n".join(
            [
                "最终输出：资料不足",
                "当前没有足够高置信度资料支撑方案生成。请补充素材、降低限定条件，或检查资料权限。",
                *_format_warnings(state.warnings),
            ]
        )
        return

    status_line = (
        "最终输出：需人工复核"
        if state.status == STATUS_NEED_HUMAN_REVIEW
        else "最终方案"
    )
    blocks = [
        status_line,
        f"任务识别：{state.intent}",
        f"关键词：{'、'.join(state.keywords)}",
        f"风格：{state.style}",
        state.cultural_review,
        state.design_plan,
        state.marketing_copy,
    ]
    if state.warnings:
        blocks.append("人工复核提示：")
        blocks.extend(f"- {warning}" for warning in _unique(state.warnings))
    state.final_answer = "\n\n".join(block for block in blocks if block)
