"""IP 设计类 Agent。

- CulturalIPAgent / ProductDesignAgent：占位（未实现）
- IpDesignAgent：对话式 IP 形象设计（DeepSeek 流式多轮对话 + 中译英 prompt）
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


class IpDesignAgent:
    """对话式 IP 形象设计 Agent。"""

    agent_code = "ip_design_agent"

    async def stream_run(self, request: dict):
        """多轮对话流式生成，async generator，yield SSE 原始行。

        request: { history: [{role, content}, ...] }  完整对话历史（含最新用户输入）
        """
        import asyncio
        import json as _json

        from app.agents.ip.prompts import IP_DESIGN_SYSTEM_PROMPT
        from app.services.llm_client import llm_client

        history = request.get("history") or []
        # 只保留 role/content，防止多余字段；限制轮数控制上下文长度
        clean_history = [
            {"role": m.get("role", "user"), "content": m.get("content", "")}
            for m in history
            if m.get("content")
        ][-20:]

        messages = [{"role": "system", "content": IP_DESIGN_SYSTEM_PROMPT}]
        messages.extend(clean_history)

        yield "event: start\ndata: {}\n\n"

        sentinel = object()
        q: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def _produce() -> None:
            try:
                for chunk in llm_client.stream_chat(
                    messages, temperature=0.8, max_tokens=1600
                ):
                    asyncio.run_coroutine_threadsafe(q.put(chunk), loop)
            finally:
                asyncio.run_coroutine_threadsafe(q.put(sentinel), loop)

        loop.run_in_executor(None, _produce)

        accumulated = ""
        while True:
            item = await q.get()
            if item is sentinel:
                break
            accumulated += item
            data = _json.dumps({"content": item}, ensure_ascii=False)
            yield f"event: delta\ndata: {data}\n\n"

        mode = "deepseek" if llm_client.api_key else "placeholder"
        final_payload = _json.dumps(
            {"raw": accumulated, "mode": mode}, ensure_ascii=False
        )
        yield f"event: final\ndata: {final_payload}\n\n"
        yield "event: done\ndata: {}\n\n"

    def translate_prompt(self, cn_prompt: str) -> str:
        """把中文文生图 prompt 转成英文（同步，供出图前调用）。"""
        from app.agents.ip.prompts import IP_PROMPT_TRANSLATE_PROMPT
        from app.services.llm_client import llm_client

        cn_prompt = (cn_prompt or "").strip()
        if not cn_prompt:
            return ""
        result = llm_client.chat(
            [
                {
                    "role": "user",
                    "content": IP_PROMPT_TRANSLATE_PROMPT.format(cn_prompt=cn_prompt),
                }
            ],
            temperature=0.3,
            max_tokens=500,
        )
        en = (result.get("content") or "").strip()
        # 兜底：转换失败时直接用中文（文生图模型也能接受）
        return en or cn_prompt
