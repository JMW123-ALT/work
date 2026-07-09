"""文创 Agent 的统一状态定义。

所有 LangGraph 节点都围绕这里的 Pydantic 模型读写数据。
这样后续无论接 Mock、Chroma 还是同事数据库，节点之间的数据结构都保持一致。
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


Intent = Literal["ip_design", "exhibition", "copywriting", "qa"]


class AgentStatus(str, Enum):
    """Agent 主流程状态，用于决定是否继续生成或进入异常分支。"""

    OK = "ok"
    NEED_MORE_MATERIAL = "need_more_material"
    NEED_HUMAN_REVIEW = "need_human_review"
    BLOCKED = "blocked"


class Evidence(BaseModel):
    """检索证据结构。

    这是数据库层和 Agent 层之间最重要的合同。后续同事数据库、
    Chroma 或 HTTP 检索服务都需要把结果转换成这个结构。
    """

    text: str
    source: str = "unknown"
    category: str = "unknown"
    culture_theme: str = "unknown"
    confidence: float = 0.0
    copyright_status: str = "unknown"
    risk_level: str = "low"


class AgentOutput(BaseModel):
    """预留的标准输出块结构，后续可用于更细的 JSON 输出。"""

    title: str
    content: str


class WenchuangState(BaseModel):
    """LangGraph 全局状态。

    每个节点只更新自己负责的字段，LangGraph 会把这些局部更新合并回总状态。
    """

    user_query: str
    intent: Intent | None = None
    keywords: list[str] = Field(default_factory=list)
    style: str = "国潮厚重风"
    evidence: list[Evidence] = Field(default_factory=list)
    cultural_review: str = ""
    design_plan: str = ""
    marketing_copy: str = ""
    warnings: list[str] = Field(default_factory=list)
    status: AgentStatus = AgentStatus.OK
    final_answer: str = ""
