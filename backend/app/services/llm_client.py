"""DeepSeek LLM 客户端。

所有直接访问 LLM API 的逻辑都集中在这里：
- `chat()`：通用 OpenAI-compatible chat 调用，供 Agent 节点使用。
- `generate_answer()`：普通 RAG 问答兼容接口。
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from typing import Any

from openai import OpenAI

from app.core.config import settings


_SYSTEM_PROMPT = (
    "你是一个文旅文创知识问答助手。请根据下方提供的参考资料，"
    "用简洁、准确的中文回答用户问题。如果参考资料不足以回答，"
    "请如实告知，不要编造信息。回答时直接给出内容。"
)


def _build_context(sources: list[dict]) -> str:
    if not sources:
        return "（当前资料库未检索到相关内容）"
    parts = []
    for i, item in enumerate(sources, 1):
        title = item.get("title") or item.get("culture_theme") or ""
        content = item.get("content") or item.get("snippet") or item.get("text") or ""
        parts.append(f"[{i}] 《{title}》\n{content}")
    return "\n\n".join(parts)


class LLMClient:
    """DeepSeek Chat 客户端。"""

    def __init__(
        self,
        *,
        openai_client: Any | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        max_retries: int = 2,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.deepseek_api_key
        self.base_url = base_url or settings.deepseek_base_url
        self.max_retries = max(1, int(max_retries))
        self.model = settings.deepseek_model
        if model:
            self.model = model
        self._client = openai_client

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> dict[str, str]:
        if self.api_key:
            return self._chat_deepseek(messages, temperature, max_tokens)
        return {
            "content": "（当前为占位回答；填写 DEEPSEEK_API_KEY 后将调用 DeepSeek 生成。）",
            "model": self.model,
            "mode": "placeholder",
        }

    def generate_answer(
        self, question: str, sources: list[dict], permission_notice: str = ""
    ) -> dict:
        context = _build_context(sources)
        user_content = f"参考资料：\n{context}\n\n用户问题：{question}"
        result = self.chat(
            [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        answer = result["content"]
        if result["mode"] == "placeholder":
            answer = self._placeholder_answer(question, sources)
        if permission_notice:
            answer += f"\n\n{permission_notice}"
        return {"answer": answer, "model": result["model"], "mode": result["mode"]}

    def _chat_deepseek(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> dict[str, str]:
        for attempt in range(1, self.max_retries + 1):
            try:
                result = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,
                )
                choice = result.choices[0]
                content = (choice.message.content or "").strip()
                if not content:
                    logging.getLogger("app").warning(
                        "DeepSeek returned empty content; finish_reason=%s",
                        getattr(choice, "finish_reason", None),
                    )
                    return {
                        "content": "（DeepSeek 未返回正式内容，已回退到本地占位回答。）",
                        "model": self.model,
                        "mode": "placeholder",
                    }
                return {
                    "content": content,
                    "model": self.model,
                    "mode": "deepseek",
                }
            except Exception as exc:
                if attempt >= self.max_retries:
                    logging.getLogger("app").error("DeepSeek API error: %s", exc)
                    return {
                        "content": "（DeepSeek 调用失败，已回退到本地占位回答。）",
                        "model": self.model,
                        "mode": "placeholder",
                    }
                logging.getLogger("app").warning(
                    "DeepSeek API attempt %s/%s failed: %s",
                    attempt,
                    self.max_retries,
                    exc,
                )
                time.sleep(0.3 * attempt)

        return {
            "content": "（DeepSeek 调用失败，已回退到本地占位回答。）",
            "model": self.model,
            "mode": "placeholder",
        }

    def stream_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> Iterator[str]:
        if not self.api_key:
            yield "（当前为占位回答；填写 DEEPSEEK_API_KEY 后将调用 DeepSeek 生成。）"
            return

        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                content = getattr(chunk.choices[0].delta, "content", None)
                if content:
                    yield content
        except Exception as exc:
            logging.getLogger("app").error("DeepSeek stream API error: %s", exc)
            yield "（DeepSeek 流式调用失败，请稍后重试或使用普通对话接口。）"

    def _placeholder_answer(self, question: str, sources: list[dict]) -> str:
        if not sources:
            return "当前资料库没有检索到足够相关的内容，建议补充资料或换一种问法。"
        titles = "、".join(
            item.get("title") or item.get("culture_theme") or "未命名资料"
            for item in sources[:3]
        )
        return (
            f"根据当前资料库，问题「{question}」可以先参考：{titles}。\n"
            "（当前为占位回答；填写 DEEPSEEK_API_KEY 后将基于 rerank 后的 chunks 生成完整回答。）"
        )


llm_client = LLMClient()
