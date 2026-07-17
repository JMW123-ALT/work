"""IP 设计类 Agent 扩展口。

以下 Agent 均为未来扩展占位，当前明确抛出 NotImplementedError。
"""

from __future__ import annotations


class CulturalIPAgent:
    """文创 IP 统筹 Agent — 未实现。"""

    agent_code = "cultural_ip_orchestrator_agent"

    async def run(self, request: dict) -> dict:
        raise NotImplementedError(
            f"Agent '{self.agent_code}' is not yet implemented."
        )


class ProductDesignAgent:
    """单项目文创子 Agent — 未实现。"""

    agent_code = "project_cultural_product_sub_agent"

    async def run(self, request: dict) -> dict:
        raise NotImplementedError(
            f"Agent '{self.agent_code}' is not yet implemented."
        )
