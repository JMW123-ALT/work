"""文创 Agent 内部工具函数。

这些私有函数被 nodes.py / fallbacks.py / guardrails.py 共用，
不对包外暴露，名称保留原 services/agent.py 中的下划线前缀。
"""

from __future__ import annotations

import inspect
import json
import re
from typing import Any

from app.agents.common.types import AgentLLM, Evidence
from app.agents.wenchuang.prompts import AGENT_SYSTEM_PROMPT


# ── 字符串 / 列表工具 ────────────────────────────────────────────────────────

def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def _unique(items) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
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


# ── 关键词 / 风格 / 产品提取 ──────────────────────────────────────────────────

STYLE_KEYWORDS = (
    "国潮厚重风",
    "潮玩年轻化风",
    "极简博物馆风",
    "短视频网红风",
    "生态休闲风",
)


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


# ── Evidence 转换 ─────────────────────────────────────────────────────────────

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


# ── Evidence prompt 格式化 ────────────────────────────────────────────────────

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


# ── LLM 调用辅助 ──────────────────────────────────────────────────────────────

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


def _is_placeholder_or_empty(text: str) -> bool:
    cleaned = (text or "").strip()
    return not cleaned or "当前为占位回答" in cleaned or "资料库没有检索到" in cleaned


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


async def _llm_text_or_fallback(
    state: Any,          # WenchuangState — 避免循环导入，用 Any
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
