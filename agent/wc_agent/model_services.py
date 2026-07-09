"""Embedding 与 Rerank 模型服务边界。

这两个客户端用于接入同事使用的阿里云百炼/MAAS 模型：

- `qwen3-vl-embedding`：把用户 query 转成向量，用于 Chroma query_embeddings。
- `qwen3-rerank`：对 Chroma 初召回结果做二次重排。

主流程不直接依赖这些 API；检索器会在配置存在时使用它们，配置缺失时自动降级。
"""

from __future__ import annotations

from typing import Any

import httpx
from openai import OpenAI

from .settings import Settings, get_settings
from .state import Evidence


class EmbeddingClient:
    """Embedding 客户端。

    qwen3-vl-embedding 走 DashScope 原生多模态接口；普通文本 embedding
    模型可继续走 OpenAI-compatible `/embeddings`。
    """

    def __init__(self, settings: Settings | None = None, timeout: float = 30.0) -> None:
        self.settings = settings or get_settings()
        self.timeout = timeout
        self._client: OpenAI | None = None
        if (
            self.settings.embedding_api_key
            and self.settings.embedding_base_url
            and not is_multimodal_embedding_model(self.settings.embedding_model)
        ):
            self._client = OpenAI(
                api_key=self.settings.embedding_api_key,
                base_url=self.settings.embedding_base_url,
                timeout=timeout,
            )

    def embed_text(self, text: str) -> list[float] | None:
        """把文本转成向量；未配置 API 时返回 None。"""

        if not self.settings.embedding_api_key:
            return None
        if is_multimodal_embedding_model(self.settings.embedding_model):
            return self._embed_multimodal_text(text)
        if not self._client:
            return None

        response = self._client.embeddings.create(
            model=self.settings.embedding_model,
            input=text,
        )
        return list(response.data[0].embedding)

    def _embed_multimodal_text(self, text: str) -> list[float] | None:
        """调用 DashScope 原生多模态 embedding 接口生成纯文本 query 向量。"""

        if not self.settings.embedding_dashscope_url:
            return None

        endpoint = self._multimodal_endpoint()
        payload = {
            "model": self.settings.embedding_model,
            "input": {"contents": [{"text": (text or "").strip() or " "}]},
            "parameters": {"enable_fusion": True},
        }
        headers = {
            "Authorization": f"Bearer {self.settings.embedding_api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        return list(data["output"]["embeddings"][0]["embedding"])

    def _multimodal_endpoint(self) -> str:
        """生成 qwen3-vl-embedding 原生接口 endpoint。"""

        base_url = self.settings.embedding_dashscope_url.rstrip("/")
        if base_url.endswith("/services/embeddings/multimodal-embedding/multimodal-embedding"):
            return base_url
        return f"{base_url}/services/embeddings/multimodal-embedding/multimodal-embedding"


class RerankClient:
    """DashScope/MAAS rerank 客户端。

    当前按阿里 DashScope rerank 请求格式实现。未配置 key 或未开启
    `RERANK_ENABLED=true` 时，会原样返回 Chroma 初召回结果。
    """

    def __init__(self, settings: Settings | None = None, timeout: float = 30.0) -> None:
        self.settings = settings or get_settings()
        self.timeout = timeout

    def rerank(self, query: str, evidence: list[Evidence], top_n: int) -> list[Evidence]:
        """对 Evidence 列表做重排。"""

        if not self.settings.rerank_enabled or not self.settings.rerank_api_key or not self.settings.rerank_base_url:
            return evidence[:top_n]
        if not evidence:
            return []

        endpoint = self._endpoint()
        documents = [item.text for item in evidence]
        payload = {
            "model": self.settings.rerank_model,
            "input": {"query": query, "documents": documents},
            "parameters": {"top_n": top_n, "return_documents": False},
        }
        headers = {
            "Authorization": f"Bearer {self.settings.rerank_api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        return self._apply_scores(evidence, data, top_n)

    def _endpoint(self) -> str:
        """生成 rerank API endpoint。"""

        base_url = self.settings.rerank_base_url.rstrip("/")
        if base_url.endswith("/services/rerank/text-rerank/text-rerank"):
            return base_url
        return f"{base_url}/services/rerank/text-rerank/text-rerank"

    def _apply_scores(self, evidence: list[Evidence], data: dict[str, Any], top_n: int) -> list[Evidence]:
        """把 rerank 返回分数写回 Evidence.confidence。"""

        results = data.get("output", {}).get("results", [])
        ranked: list[Evidence] = []
        for item in results:
            index = int(item.get("index", -1))
            if 0 <= index < len(evidence):
                score = float(item.get("relevance_score", evidence[index].confidence))
                ranked.append(replace_evidence_confidence(evidence[index], score))
        return ranked[:top_n] if ranked else evidence[:top_n]


def replace_evidence_confidence(evidence: Evidence, confidence: float) -> Evidence:
    """兼容 Pydantic v2 的 Evidence 拷贝更新。"""

    return evidence.model_copy(update={"confidence": max(0.0, min(1.0, confidence))})


def is_multimodal_embedding_model(model: str) -> bool:
    """通过模型名判断是否需要走 DashScope 原生多模态 embedding 接口。"""

    model_name = model.lower()
    return "vl" in model_name or "multimodal" in model_name
