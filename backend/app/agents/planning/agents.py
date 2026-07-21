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
    """图片 Prompt 生成 Agent — 使用 DeepSeek 生成结构化提示词。"""

    agent_code = "image_prompt_agent"

    async def run(self, request: dict) -> dict:
        import json
        import re

        from app.agents.planning.prompts import (
            IMAGE_PROMPT_SYSTEM_PROMPT,
            IMAGE_PROMPT_USER_TEMPLATE,
        )
        from app.services.llm_client import llm_client

        theme = request.get("theme", "")
        style = request.get("style", "")
        ratio = request.get("ratio", "1:1")
        extra = request.get("extra", "")

        user_msg = IMAGE_PROMPT_USER_TEMPLATE.format(
            theme=theme, style=style, ratio=ratio, extra=extra or "无"
        )
        result = llm_client.chat(
            [
                {"role": "system", "content": IMAGE_PROMPT_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.6,
            max_tokens=1024,
        )
        raw: str = result.get("content", "")

        # 尝试解析 JSON（兼容 LLM 可能包裹 ```json ... ``` 的情况）
        try:
            clean = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
            parsed = json.loads(clean)
            return {
                "prompt": parsed.get("prompt", ""),
                "negative_prompt": parsed.get("negative_prompt", ""),
                "style": parsed.get("style", style),
                "ratio": parsed.get("ratio", ratio),
                "model_suggestion": parsed.get("model_suggestion", "gpt-image-2"),
                "mode": parsed.get("mode", "text-to-image"),
            }
        except (json.JSONDecodeError, Exception):
            # JSON 解析失败时返回兜底结构，不抛 500
            fallback_prompt = raw[:500] if raw else f"{theme}，{style}风格，高清细节"
            return {
                "prompt": fallback_prompt,
                "negative_prompt": "低质量、模糊、水印、变形",
                "style": style,
                "ratio": ratio,
                "model_suggestion": "gpt-image-2",
                "mode": "text-to-image",
            }
