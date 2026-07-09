"""统一 LLM 调用封装。

当前通过 OpenAI-compatible 协议调用 DeepSeek；如果没有配置 API Key，
会自动降级到本地 mock，方便在没有网络或没有 Key 时测试 Agent 流程。
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from .settings import Settings, get_settings


class UnifiedLLM:
    """统一大模型客户端，向上屏蔽不同供应商的调用细节。"""

    def __init__(self, settings: Settings | None = None, timeout: float = 60.0) -> None:
        self.settings = settings or get_settings()
        self.timeout = timeout
        self._client: AsyncOpenAI | None = None
        if self.settings.llm_api_key:
            self._client = AsyncOpenAI(
                api_key=self.settings.llm_api_key,
                base_url=self.settings.llm_base_url,
                timeout=timeout,
            )

    async def chat(self, system: str, user: str, temperature: float = 0.3) -> str:
        """普通非流式调用，返回完整文本。"""

        if not self._client:
            return self._mock_response(system, user)

        response = await self._client.chat.completions.create(
            model=self.settings.llm_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        content = response.choices[0].message.content or ""
        return content.strip()

    async def stream_chat(self, system: str, user: str, temperature: float = 0.3) -> AsyncIterator[str]:
        """流式调用，逐块 yield 模型输出。

        FastAPI 的 `/llm/stream` 接口会直接消费这个异步迭代器。
        """
        if not self._client:
            mock = self._mock_response(system, user)
            for index in range(0, len(mock), 16):
                yield mock[index : index + 16]
            return

        stream = await self._client.chat.completions.create(
            model=self.settings.llm_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    @staticmethod
    def _mock_response(system: str, user: str) -> str:
        """本地固定回答。

        mock 的目标不是生成高质量内容，而是在没有真实模型时保证流程可跑通。
        """

        if "创意设计" in system:
            return (
                "产品定位：面向年轻游客与博物馆文创消费场景的实用型文创。\n"
                "设计思路：以可追溯文化元素为主视觉，结合现代产品结构做克制转译。\n"
                "产品款式：基础款、礼盒款、联名展陈款。\n"
                "落地建议：先做低保真视觉稿，再进入材质、工艺、打样评审。"
            )
        if "营销优化" in system:
            return (
                "小红书标题：把传统纹样带进日常的一杯东方美学。\n"
                "小红书正文：从文化元素出发，讲清来源、设计亮点和使用场景。\n"
                "抖音脚本：3 秒视觉钩子 -> 文化溯源 -> 产品细节 -> 购买/参观引导。\n"
                "电商卖点：文化可溯源、设计有节制、适合送礼与馆藏纪念。"
            )
        if "文化考据" in system:
            return (
                "文化溯源：基于检索史料提取核心文化元素，暂不扩写无依据背景。\n"
                "可用元素：纹样、色彩、器物形制、历史语境。\n"
                "禁用/慎用点：不得虚构朝代、人物、工艺传承；版权不明素材不得商用。\n"
                "人工核验点：正式上线前需由文博/非遗专家确认史料准确性。"
            )
        return f"已识别任务：{user[:120]}"
