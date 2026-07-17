"""意图代码常量（扩展口）。

未来在此维护 AgentRouter 使用的意图代码 → agent_code 映射表。
"""

from __future__ import annotations

# 意图代码（与 wenchuang/state.py 中的 INTENT_* 保持一致）
INTENT_IP_DESIGN = "ip_design"
INTENT_EXHIBITION = "exhibition"
INTENT_COPYWRITING = "copywriting"
INTENT_QA = "qa"
INTENT_PLANNING = "planning"

# 意图 → agent_code 路由表（待实现）
INTENT_TO_AGENT_CODE: dict[str, str] = {
    # INTENT_PLANNING: "planning_outline_agent",
    # INTENT_IP_DESIGN: "cultural_ip_orchestrator_agent",
    # INTENT_COPYWRITING: "xiaohongshu_sub_agent",
}
