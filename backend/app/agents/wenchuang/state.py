"""文创 Agent 内部状态与常量。

AgentGraphState 是 LangGraph 私有结构，不从 services/agent.py facade 导出。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, TypedDict


# ── 状态常量 ─────────────────────────────────────────────────────────────────

STATUS_OK = "ok"
STATUS_NEED_MORE_MATERIAL = "need_more_material"
STATUS_NEED_HUMAN_REVIEW = "need_human_review"
STATUS_BLOCKED = "blocked"

# ── 意图常量 ─────────────────────────────────────────────────────────────────

INTENT_IP_DESIGN = "ip_design"
INTENT_EXHIBITION = "exhibition"
INTENT_COPYWRITING = "copywriting"
INTENT_QA = "qa"
INTENT_PLANNING = "planning"


# ── 运行状态 dataclass ────────────────────────────────────────────────────────

@dataclass(slots=True)
class WenchuangState:
    """文创 Agent 在 LangGraph 中贯穿整个工作流的可变状态。"""

    user_query: str
    intent: str = ""
    keywords: list[str] = field(default_factory=list)
    style: str = "未指定"
    evidence: list[Any] = field(default_factory=list)   # list[Evidence]
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


# ── LangGraph 图状态（仅文创包内使用）────────────────────────────────────────

class AgentGraphState(TypedDict):
    state: WenchuangState
