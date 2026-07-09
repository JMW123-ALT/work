"""
LLM 客户端（DeepSeek）
- deepseek_api_key 为空 → 返回本地占位答案
- deepseek_api_key 非空 → 调用 DeepSeek Chat API（OpenAI 兼容接口）

接口文档：https://platform.deepseek.com/api-docs/
"""
import json

from app.core.config import settings

# DeepSeek chat endpoint（OpenAI 兼容）
_CHAT_URL = f"{settings.deepseek_base_url}/chat/completions"

_SYSTEM_PROMPT = (
    "你是一个旅游知识问答助手。请根据下方提供的参考资料，用简洁、准确的中文回答用户问题。"
    "如果参考资料不足以回答，请如实告知，不要编造信息。"
    "回答时直接给出内容，不要重复引用原文的格式标注。"
)


def _build_context(sources: list[dict]) -> str:
    """将检索到的 chunks 拼接为 prompt 上下文"""
    if not sources:
        return "（当前资料库未检索到相关内容）"
    parts = []
    for i, item in enumerate(sources, 1):
        title = item.get("title", "")
        content = item.get("content") or item.get("snippet") or ""
        parts.append(f"[{i}] 《{title}》\n{content}")
    return "\n\n".join(parts)


class LLMClient:
    """DeepSeek 问答客户端。

    这是项目中唯一应该直接调用 LLM 的地方。
    RAGService 在过滤、rerank 之后把 chunks 传入这里生成最终回答。
    """

    def __init__(self) -> None:
        self.model = settings.deepseek_model

    # ── 公共接口 ──────────────────────────────────────────────────

    def generate_answer(
        self, question: str, sources: list[dict], permission_notice: str = ""
    ) -> dict:
        if settings.deepseek_api_key:
            return self._generate_deepseek(question, sources, permission_notice)
        return self._generate_placeholder(question, sources, permission_notice)

    # ── 本地占位回答 ───────────────────────────────────────────────

    def _generate_placeholder(
        self, question: str, sources: list[dict], permission_notice: str = ""
    ) -> dict:
        if not sources:
            answer = "当前资料库没有检索到足够相关的内容，建议补充资料或换一种问法。"
        else:
            titles = "、".join(item.get("title", "") for item in sources[:3])
            answer = (
                f"根据当前资料库，问题「{question}」可以先参考：{titles}。\n"
                "（当前为占位回答；填写 DEEPSEEK_API_KEY 后将基于 rerank 后的 chunks 生成完整回答。）"
            )
        if permission_notice:
            answer += f"\n\n{permission_notice}"
        return {"answer": answer, "model": self.model, "mode": "placeholder"}

    # ── DeepSeek Chat API ─────────────────────────────────────────

    def _generate_deepseek(
        self, question: str, sources: list[dict], permission_notice: str = ""
    ) -> dict:
        """调用 DeepSeek Chat API（OpenAI 兼容格式）。

        使用 deepseek-chat 模型，将检索到的 chunks 作为上下文注入 user 消息。
        """
        import urllib.request
        import urllib.error

        context = _build_context(sources)
        user_content = (
            f"参考资料：\n{context}\n\n"
            f"用户问题：{question}"
        )

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        payload = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 1024,
                "stream": False,
            },
            ensure_ascii=False,
        ).encode("utf-8")

        req = urllib.request.Request(
            _CHAT_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.deepseek_api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            answer = result["choices"][0]["message"]["content"].strip()
            if permission_notice:
                answer += f"\n\n{permission_notice}"
            return {"answer": answer, "model": self.model, "mode": "deepseek"}

        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            import logging
            logging.getLogger("app").error("DeepSeek API HTTPError %s: %s", exc.code, body)
            return self._generate_placeholder(question, sources, permission_notice)
        except Exception as exc:
            import logging
            logging.getLogger("app").error("DeepSeek API error: %s", exc)
            return self._generate_placeholder(question, sources, permission_notice)


llm_client = LLMClient()
