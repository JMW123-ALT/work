"""文创 Agent 服务。

流程：需求解析 -> 前置风控 -> 内部 RAG 检索 -> 后置风控 ->
DeepSeek 文化考据 -> DeepSeek 方案设计 -> DeepSeek 传播文案 -> 汇总输出。
"""

from __future__ import annotations

import asyncio
import inspect
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol, TypedDict

from langgraph.graph import END, StateGraph


STATUS_OK = "ok"
STATUS_NEED_MORE_MATERIAL = "need_more_material"
STATUS_NEED_HUMAN_REVIEW = "need_human_review"
STATUS_BLOCKED = "blocked"

INTENT_IP_DESIGN = "ip_design"
INTENT_EXHIBITION = "exhibition"
INTENT_COPYWRITING = "copywriting"
INTENT_QA = "qa"
INTENT_PLANNING = "planning"

ALLOWED_COPYRIGHT_STATUSES = {"public_domain", "authorized"}
HIGH_RISK_INPUT_TERMS = (
    "恶搞烈士",
    "侮辱烈士",
    "篡改历史",
    "历史虚无主义",
    "低俗化",
    "丑化传统文化",
    "辱华",
)
PROTECTED_IP_TERMS = (
    "迪士尼",
    "漫威",
    "哈利波特",
    "宝可梦",
    "知名ip",
    "ip联名",
    "商用ip",
)
STYLE_KEYWORDS = (
    "国潮厚重风",
    "潮玩年轻化风",
    "极简博物馆风",
    "短视频网红风",
    "生态休闲风",
)

AGENT_SYSTEM_PROMPT = (
    "你是一个资深文旅与文创策划 Agent，擅长基于已入库资料做文化考据、"
    "空间/产品/活动方案设计和传播文案。必须严格依据提供的 evidence，"
    "不得编造资料来源；资料不足时要明确提示。输出中文，结构清晰，可落地。"
)


@dataclass(slots=True)
class Evidence:
    text: str
    source: str = ""
    category: str = ""
    culture_theme: str = ""
    confidence: float = 0.0
    copyright_status: str = "unknown"
    risk_level: str = "low"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WenchuangState:
    user_query: str
    intent: str = ""
    keywords: list[str] = field(default_factory=list)
    style: str = "未指定"
    evidence: list[Evidence] = field(default_factory=list)
    cultural_review: str = ""
    design_plan: str = ""
    marketing_copy: str = ""
    warnings: list[str] = field(default_factory=list)
    llm_modes: dict[str, str] = field(default_factory=dict)
    workflow: str = "langgraph"
    status: str = STATUS_OK
    final_answer: str = ""

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["evidence"] = [asdict(item) for item in self.evidence]
        return result


class Retriever(Protocol):
    def search(self, query: str, n_results: int = 5) -> list[Evidence | dict[str, Any]]:
        ...


class AgentLLM(Protocol):
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> dict[str, str]:
        ...


class AgentGraphState(TypedDict):
    state: WenchuangState


class RAGServiceRetriever:
    """把现有 RAGService.search 适配成 Agent Evidence 检索器。"""

    def __init__(self, user_type: str = "visitor", min_confidence: float = 0.0) -> None:
        self.user_type = user_type
        self.min_confidence = min_confidence

    def search(self, query: str, n_results: int = 5) -> list[dict[str, Any]]:
        from app.services.rag_service import rag_service

        # Agent needs to know whether low-confidence candidates exist so it can
        # produce a reviewable draft instead of hiding all evidence too early.
        result = rag_service.search(
            {
                "query": query,
                "user_type": self.user_type,
                "top_k": n_results,
                "min_confidence": 0.0,
            }
        )
        return result["items"]


class WenchuangAgent:
    def __init__(
        self,
        retriever: Retriever | None = None,
        llm: AgentLLM | None = None,
    ) -> None:
        self.retriever = retriever or RAGServiceRetriever()
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
        graph = self._build_graph(n_results=n_results, min_confidence=min_confidence)
        result = await graph.ainvoke({"state": state})
        return result["state"].to_dict()

    def _build_graph(self, *, n_results: int, min_confidence: float):
        graph = StateGraph(AgentGraphState)

        async def intent_step(graph_state: AgentGraphState) -> AgentGraphState:
            intent_node(graph_state["state"])
            return graph_state

        async def pre_guardrails_step(graph_state: AgentGraphState) -> AgentGraphState:
            pre_guardrails_node(graph_state["state"])
            return graph_state

        async def llm_intent_step(graph_state: AgentGraphState) -> AgentGraphState:
            await llm_intent_node(graph_state["state"], self.llm)
            return graph_state

        async def retrieve_step(graph_state: AgentGraphState) -> AgentGraphState:
            await retrieve_node(
                graph_state["state"],
                self.retriever,
                n_results,
                min_confidence,
            )
            return graph_state

        async def post_guardrails_step(graph_state: AgentGraphState) -> AgentGraphState:
            post_guardrails_node(graph_state["state"])
            return graph_state

        async def cultural_review_step(graph_state: AgentGraphState) -> AgentGraphState:
            await cultural_review_node(graph_state["state"], self.llm)
            return graph_state

        async def design_step(graph_state: AgentGraphState) -> AgentGraphState:
            await design_node(graph_state["state"], self.llm)
            return graph_state

        async def marketing_step(graph_state: AgentGraphState) -> AgentGraphState:
            await marketing_node(graph_state["state"], self.llm)
            return graph_state

        async def final_step(graph_state: AgentGraphState) -> AgentGraphState:
            final_node(graph_state["state"])
            return graph_state

        def after_pre_guardrails(graph_state: AgentGraphState) -> str:
            if graph_state["state"].status == STATUS_BLOCKED:
                return "final"
            return "llm_intent"

        graph.add_node("intent", intent_step)
        graph.add_node("pre_guardrails", pre_guardrails_step)
        graph.add_node("llm_intent", llm_intent_step)
        graph.add_node("retrieve", retrieve_step)
        graph.add_node("post_guardrails", post_guardrails_step)
        graph.add_node("cultural_review", cultural_review_step)
        graph.add_node("design", design_step)
        graph.add_node("marketing", marketing_step)
        graph.add_node("final", final_step)

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


async def run_agent(
    user_query: str,
    *,
    retriever: Retriever | None = None,
    llm: AgentLLM | None = None,
    n_results: int = 5,
    min_confidence: float = 0.7,
) -> dict[str, Any]:
    return await WenchuangAgent(retriever=retriever, llm=llm).run(
        user_query,
        n_results=n_results,
        min_confidence=min_confidence,
    )


def run_agent_sync(
    user_query: str,
    *,
    retriever: Retriever | None = None,
    llm: AgentLLM | None = None,
    n_results: int = 5,
    min_confidence: float = 0.7,
) -> dict[str, Any]:
    return asyncio.run(
        run_agent(
            user_query,
            retriever=retriever,
            llm=llm,
            n_results=n_results,
            min_confidence=min_confidence,
        )
    )


def intent_node(state: WenchuangState) -> None:
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
    prompt = (
        "请做文创/文旅需求解析，并只输出 JSON，不要 Markdown。\n"
        "JSON 字段：intent、keywords、style。\n"
        "intent 只能是 ip_design、exhibition、copywriting、qa、planning。\n"
        f"用户需求：{state.user_query}"
    )
    result = await _llm_chat_result(
        llm,
        prompt,
        temperature=0.1,
        max_tokens=800,
    )
    state.llm_modes["intent"] = str(result.get("mode") or "unknown")
    parsed = _json_object(str(result.get("content") or ""))
    if not parsed:
        return

    intent = str(parsed.get("intent") or "").strip()
    if intent in {
        INTENT_IP_DESIGN,
        INTENT_EXHIBITION,
        INTENT_COPYWRITING,
        INTENT_QA,
        INTENT_PLANNING,
    }:
        state.intent = intent

    keywords = parsed.get("keywords")
    if isinstance(keywords, list):
        cleaned = [str(item).strip() for item in keywords if str(item).strip()]
        if cleaned:
            state.keywords = cleaned

    style = str(parsed.get("style") or "").strip()
    if style:
        state.style = style


def pre_guardrails_node(state: WenchuangState) -> None:
    if _has_any(state.user_query, HIGH_RISK_INPUT_TERMS):
        state.status = STATUS_BLOCKED
        state.warnings.append(
            "命中文化安全高风险表达，已停止生成；请调整为尊重史实和传统文化的需求。"
        )
        return

    if _has_any(state.user_query, PROTECTED_IP_TERMS):
        state.status = STATUS_NEED_HUMAN_REVIEW
        state.warnings.append("输入疑似包含受保护商用 IP，最终方案必须进行版权/授权人工复核。")


async def retrieve_node(
    state: WenchuangState,
    retriever: Retriever,
    n_results: int,
    min_confidence: float,
) -> None:
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


def post_guardrails_node(state: WenchuangState) -> None:
    if state.status == STATUS_NEED_MORE_MATERIAL:
        return

    for item in state.evidence:
        if item.copyright_status not in ALLOWED_COPYRIGHT_STATUSES:
            state.status = STATUS_NEED_HUMAN_REVIEW
            state.warnings.append(
                f"证据 {item.source or 'unknown'} 版权状态为 {item.copyright_status}，需授权复核。"
            )
        if item.risk_level in {"medium", "high"}:
            state.status = STATUS_NEED_HUMAN_REVIEW
            state.warnings.append(
                f"证据 {item.source or 'unknown'} 风险等级为 {item.risk_level}，需人工复核。"
            )
        if item.metadata.get("is_controversial"):
            state.status = STATUS_NEED_HUMAN_REVIEW
            state.warnings.append(
                f"证据 {item.source or 'unknown'} 标记为争议资料，需补充多方观点并人工核验。"
            )


async def cultural_review_node(state: WenchuangState, llm: AgentLLM) -> None:
    if state.status == STATUS_NEED_MORE_MATERIAL:
        state.cultural_review = "资料不足，无法完成可靠文化考据。"
        return

    prompt = (
        "请基于 evidence 做文化考据/项目依据梳理。\n"
        "要求：只使用 evidence，不编造；输出包括：资料依据、可用元素、谨慎点、人工核验点。\n"
        f"用户需求：{state.user_query}\n"
        f"当前意图：{state.intent}\n"
        f"风险提示：{_join_or_default(state.warnings, '无')}\n\n"
        f"evidence：\n{_format_evidence_for_prompt(state.evidence)}"
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
    if state.status in {STATUS_BLOCKED, STATUS_NEED_MORE_MATERIAL}:
        return

    prompt = (
        "请基于 evidence 和文化考据输出方案设计。\n"
        "如果是公园/景区/概念方案，请输出：项目定位、主题结构、空间/游线、业态活动、运营建议、落地优先级。\n"
        "如果是文创产品，请输出：产品定位、设计语言、视觉元素、工艺建议、落地建议。\n"
        "不得编造 evidence 外的项目事实。\n"
        f"用户需求：{state.user_query}\n"
        f"意图：{state.intent}\n"
        f"风格：{state.style}\n\n"
        f"文化考据：\n{state.cultural_review}\n\n"
        f"evidence：\n{_format_evidence_for_prompt(state.evidence)}"
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
    if state.status in {STATUS_BLOCKED, STATUS_NEED_MORE_MATERIAL}:
        return

    prompt = (
        "请基于方案设计输出传播文案。\n"
        "要求包括：一句话定位、公众号/小红书文案、短视频口播、电商或招商卖点。"
        "表达要具体，避免空泛。\n"
        f"用户需求：{state.user_query}\n\n"
        f"方案设计：\n{state.design_plan}"
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


def _fallback_cultural_review(state: WenchuangState) -> str:
    themes = _unique(item.culture_theme for item in state.evidence if item.culture_theme)
    source_lines = [
        f"- {item.culture_theme or item.category or '资料'}：{_short_text(item.text)}（来源：{item.source or 'unknown'}）"
        for item in state.evidence[:5]
    ]
    caution = "；".join(state.warnings) if state.warnings else "当前未发现重大文化安全或版权风险。"
    return "\n".join(
        [
            "文化溯源与可用元素：",
            *(source_lines or ["- 已检索到可参考素材，但主题字段仍需补全。"]),
            f"建议主线：围绕{_join_or_default(themes, '检索到的资料主题')}提炼空间、产品、活动和叙事线索。",
            f"慎用与核验点：{caution}",
        ]
    )


def _fallback_design_plan(state: WenchuangState) -> str:
    product = _detect_product(state.user_query)
    themes = _join_or_default(
        _unique(item.culture_theme for item in state.evidence if item.culture_theme),
        "已检索资料",
    )
    style = state.style if state.style != "未指定" else "文旅项目现代化表达"
    return "\n".join(
        [
            "方案设计：",
            f"1. 项目定位：以{themes}为依据，形成{product}方向。",
            f"2. 设计语言：采用{style}，保留资料中的真实项目信息。",
            "3. 空间/产品结构：从检索资料中提取主题、节点、游线和运营场景。",
            "4. 落地建议：优先选择可实施、可运营、可传播的模块。",
            "5. 合规要求：落地前复核资料、版权授权和争议内容。",
        ]
    )


def _fallback_marketing_copy(state: WenchuangState) -> str:
    product = _detect_product(state.user_query)
    themes = _join_or_default(
        _unique(item.culture_theme for item in state.evidence if item.culture_theme),
        "项目资料",
    )
    return "\n".join(
        [
            "传播文案：",
            f"一句话定位：基于{themes}，打造可游、可停留、可传播的{product}。",
            f"小红书文案：把{themes}带进日常体验，用一条路线、一个场景或一件产品讲清楚项目价值。",
            "短视频口播：走进这个项目，看见城市与自然重新连接的方式。",
            "推广卖点：资料依据清晰；场景可落地；适合文旅消费、亲子活动和公共空间运营。",
        ]
    )


def _to_evidence(item: Evidence | dict[str, Any]) -> Evidence:
    if isinstance(item, Evidence):
        return item
    return Evidence(
        text=str(item.get("text") or item.get("content") or item.get("snippet") or ""),
        source=str(item.get("source") or item.get("source_id") or ""),
        category=str(item.get("category") or item.get("object_type") or ""),
        culture_theme=str(item.get("culture_theme") or item.get("title") or ""),
        confidence=_bounded_float(item.get("confidence", item.get("score", 0))),
        copyright_status=str(item.get("copyright_status") or "unknown"),
        risk_level=str(item.get("risk_level") or "low"),
        metadata=dict(item.get("metadata") or {}),
    )


async def _llm_text_or_fallback(
    state: WenchuangState,
    node_name: str,
    llm: AgentLLM,
    prompt: str,
    fallback: str,
    *,
    max_tokens: int,
) -> str:
    result = await _llm_chat_result(llm, prompt, temperature=0.3, max_tokens=max_tokens)
    content = str(result.get("content") or "")
    mode = str(result.get("mode") or "unknown")
    if _is_placeholder_or_empty(content):
        state.llm_modes[node_name] = f"{mode}:fallback" if mode else "fallback"
        return fallback
    state.llm_modes[node_name] = mode
    return content.strip()


async def _llm_chat(
    llm: AgentLLM,
    user_prompt: str,
    *,
    temperature: float,
    max_tokens: int,
) -> str:
    result = await _llm_chat_result(
        llm,
        user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return str(result.get("content") or "")


async def _llm_chat_result(
    llm: AgentLLM,
    user_prompt: str,
    *,
    temperature: float,
    max_tokens: int,
) -> dict[str, str]:
    result = await _maybe_await(
        llm.chat(
            [
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
    )
    if isinstance(result, dict):
        return {
            "content": str(result.get("content") or result.get("answer") or ""),
            "model": str(result.get("model") or ""),
            "mode": str(result.get("mode") or "unknown"),
        }
    return {"content": str(result or ""), "model": "", "mode": "unknown"}


def _is_placeholder_or_empty(text: str) -> bool:
    cleaned = (text or "").strip()
    return not cleaned or "当前为占位回答" in cleaned or "资料库没有检索到" in cleaned


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _json_object(text: str) -> dict[str, Any] | None:
    cleaned = (text or "").strip()
    if not cleaned:
        return None
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _format_evidence_for_prompt(evidence: list[Evidence], limit: int = 5) -> str:
    parts = []
    for index, item in enumerate(evidence[:limit], 1):
        title = item.culture_theme or item.category or item.source or f"资料{index}"
        parts.append(
            "\n".join(
                [
                    f"[{index}] {title}",
                    f"source: {item.source or 'unknown'}",
                    f"confidence: {item.confidence}",
                    f"copyright_status: {item.copyright_status}",
                    f"risk_level: {item.risk_level}",
                    f"text: {_short_text(item.text, 1200)}",
                ]
            )
        )
    return "\n\n".join(parts)


def _detect_style(query: str) -> str:
    for style in STYLE_KEYWORDS:
        if style in query:
            return style
    if "国潮" in query:
        return "国潮厚重风"
    if "年轻" in query or "潮玩" in query:
        return "潮玩年轻化风"
    if "极简" in query or "博物馆风" in query:
        return "极简博物馆风"
    if "生态" in query or "郊野" in query or "公园" in query:
        return "生态休闲风"
    return "未指定"


def _extract_keywords(query: str) -> list[str]:
    normalized = re.sub(r"[，。；、,.!?！？;：:\s]+", "|", query)
    parts = [part.strip() for part in normalized.split("|") if part.strip()]
    keywords = [part for part in parts if len(part) > 1]
    if not keywords:
        keywords = [query]
    return _unique(keywords)


def _detect_product(query: str) -> str:
    for product in ("保温杯", "冰箱贴", "帆布包", "徽章", "明信片", "茶具", "香薰", "摆件"):
        if product in query:
            return product
    if "公园" in query or "景区" in query or "规划" in query or "概念方案" in query:
        return "文旅策划方案"
    if "策展" in query or "展览" in query:
        return "策展方案"
    if "文案" in query:
        return "文创内容"
    return "文创方案"


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def _unique(items) -> list[str]:
    result = []
    seen = set()
    for item in items:
        if item and item not in seen:
            result.append(item)
            seen.add(item)
    return result


def _join_or_default(items: list[str], default: str) -> str:
    return "、".join(items) if items else default


def _short_text(text: str, limit: int = 80) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "..."


def _bounded_float(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return round(min(max(number, 0.0), 1.0), 4)


def _format_warnings(warnings: list[str]) -> list[str]:
    return [f"- {warning}" for warning in _unique(warnings)]


async def _main(argv: list[str]) -> int:
    query = " ".join(argv).strip()
    if not query:
        print("Usage: python -m app.services.agent <user_query>")
        return 2
    result = await run_agent(query)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main(sys.argv[1:])))
