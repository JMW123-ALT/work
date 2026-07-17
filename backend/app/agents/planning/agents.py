"""策划类 Agent 扩展口。

以下 Agent 均为未来扩展占位，当前明确抛出 NotImplementedError。
不对外暴露任何会让调用方误以为功能可用的接口。
"""

from __future__ import annotations


class PlanningOutlineAgent:
    """策划大纲 Agent — 未实现。"""

    agent_code = "planning_outline_agent"

    async def run(self, request: dict) -> dict:
        raise NotImplementedError(
            f"Agent '{self.agent_code}' is not yet implemented. "
            "Implement in app/agents/planning/agent.py when ready."
        )


class FullTextProposalAgent:
    """策划全稿 Agent — 未实现。"""

    agent_code = "full_proposal_agent"

    async def run(self, request: dict) -> dict:
        raise NotImplementedError(
            f"Agent '{self.agent_code}' is not yet implemented."
        )


class PptProposalAgent:
    """PPT 方案统筹 Agent — 未实现。"""

    agent_code = "proposal_orchestrator_agent"

    async def run(self, request: dict) -> dict:
        raise NotImplementedError(
            f"Agent '{self.agent_code}' is not yet implemented."
        )


class ImagePromptAgent:
    """图片 Prompt 生成 Agent — 未实现。"""

    agent_code = "image_prompt_agent"

    async def run(self, request: dict) -> dict:
        raise NotImplementedError(
            f"Agent '{self.agent_code}' is not yet implemented."
        )
