"""知识库问答 Agent prompt 和消息构建工具。

所有字符串从 api/v1/agent.py 原样迁移，内容不做任何修改。
"""

from __future__ import annotations


# ── System prompt（原样移出，不修改内容） ───────────────────────────────────

KNOWLEDGE_QA_SYSTEM_PROMPT = (
    "You are a tourism and cultural-creative knowledge-base assistant. "
    "Prefer retrieved knowledge-base context when it is available. "
    "If no context is retrieved, answer directly from general knowledge instead of refusing. "
    "Do not show the retrieval list, and do not invent source citations. "
    "Answer naturally and clearly in Chinese, and keep the conversation easy to continue."
)

NO_CONTEXT_SUFFIX = (
    "\n\nNo knowledge-base context was retrieved for this turn. Answer directly."
)

CONTEXT_PREFIX = "\n\nRetrieved knowledge-base context:\n"


# ── 消息构建 ─────────────────────────────────────────────────────────────────

def build_stream_messages(req, sources: list[dict]) -> list[dict[str, str]]:
    """把请求和检索到的资料拼装成 LLM 消息列表。

    Args:
        req:     AgentChatRequest 对象（query, history）。
        sources: 已格式化的检索结果列表。

    Returns:
        OpenAI-compatible messages 列表，最新 10 条历史 + 当前 query。
    """
    system_prompt = KNOWLEDGE_QA_SYSTEM_PROMPT
    if sources:
        context = format_sources_for_prompt(sources)
        system_prompt += CONTEXT_PREFIX + context
    else:
        system_prompt += NO_CONTEXT_SUFFIX

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for item in req.history[-10:]:
        messages.append({"role": item.role, "content": item.content})
    messages.append({"role": "user", "content": req.query})
    return messages


def format_sources_for_prompt(sources: list[dict], limit: int = 5) -> str:
    """把检索结果列表格式化为 prompt 上下文字符串。"""
    parts = []
    for index, item in enumerate(sources[:limit], 1):
        title = (
            item.get("culture_theme")
            or item.get("title")
            or item.get("source")
            or f"source {index}"
        )
        text = item.get("text") or item.get("content") or item.get("snippet") or ""
        parts.append(f"[{index}] {title}\n{text}")
    return "\n\n".join(parts)
