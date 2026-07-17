"""跨 Agent 共享类型定义。

本模块只放稳定的最小结构，不放业务逻辑。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


# ── Evidence ────────────────────────────────────────────────────────────────

@dataclass(slots=True)
class Evidence:
    """单条检索证据，供任何 Agent 使用。"""

    text: str
    source: str = ""
    category: str = ""
    culture_theme: str = ""
    confidence: float = 0.0
    copyright_status: str = "unknown"
    risk_level: str = "low"
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Protocol ─────────────────────────────────────────────────────────────────

class Retriever(Protocol):
    """最小检索器协议，供测试注入 Fake。"""

    def search(self, query: str, n_results: int = 5) -> list[Evidence | dict[str, Any]]:
        ...


class AgentLLM(Protocol):
    """最小 LLM 协议，跨 Agent 可复用。"""

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> dict[str, str]:
        ...


# ── 通用运行结果结构（最小稳定接口） ───────────────────────────────────────────

@dataclass
class AgentEvent:
    """Agent 推送的单条事件（SSE 或内部通知）。"""

    event: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Agent 最终运行结果的通用包装。"""

    status: str
    agent_code: str
    output: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass
class AgentRunRequest:
    """通用 Agent 运行请求（Router 层使用）。"""

    query: str
    user_type: str = "visitor"
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRunContext:
    """运行时注入的上下文（会话 ID、租户等），当前仅占位。"""

    session_id: str = ""
    tenant_id: str = ""
    extra: dict[str, Any] = field(default_factory=dict)
