"""
Rerank 客户端
- provider=passthrough / local / "" → 直接按向量检索分数排序（无需 API）
- provider=dashscope               → 阿里 DashScope gte-rerank

接口文档：https://help.aliyun.com/zh/dashscope/developer-reference/text-rerank
"""
import json

from app.core.config import settings

# DashScope rerank endpoint
_RERANK_URL = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"


class RerankClient:
    def __init__(self) -> None:
        self.provider = settings.rerank_provider
        self.model = settings.rerank_model or "gte-rerank"

    # ── 公共接口 ──────────────────────────────────────────────────

    def rerank(self, query: str, chunks: list[dict], top_n: int = 5) -> dict:
        if self.provider == "dashscope" and settings.rerank_api_key:
            return self._rerank_dashscope(query, chunks, top_n)
        return self._passthrough(chunks, top_n)

    # ── pass-through（按向量分数直接截取） ─────────────────────────

    def _passthrough(self, chunks: list[dict], top_n: int) -> dict:
        ranked = []
        for index, item in enumerate(chunks[:top_n]):
            copied = dict(item)
            copied["rerank_score"] = copied.get("score", 0)
            copied["rerank_rank"] = index + 1
            ranked.append(copied)
        return {"items": ranked, "mode": "passthrough", "model": "passthrough"}

    # ── DashScope gte-rerank ──────────────────────────────────────

    def _rerank_dashscope(self, query: str, chunks: list[dict], top_n: int) -> dict:
        """调用阿里 DashScope gte-rerank 接口对 chunks 重排序。

        请求体：
          {
            "model": "gte-rerank",
            "input": {
              "query": "<用户问题>",
              "documents": ["<chunk content>", ...]
            },
            "parameters": {"top_n": 5, "return_documents": false}
          }

        响应体（results 数组，按相关性降序）：
          [{"index": 2, "relevance_score": 0.95}, ...]
        """
        import urllib.request

        documents = [c.get("content") or c.get("snippet") or "" for c in chunks]
        if not documents:
            return self._passthrough(chunks, top_n)

        payload = json.dumps(
            {
                "model": self.model,
                "input": {"query": query, "documents": documents},
                "parameters": {"top_n": top_n, "return_documents": False},
            },
            ensure_ascii=False,
        ).encode("utf-8")

        req = urllib.request.Request(
            _RERANK_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.rerank_api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            results = result.get("output", {}).get("results", [])
            ranked = []
            for rank_item in results:
                orig_idx = rank_item["index"]
                if orig_idx < len(chunks):
                    copied = dict(chunks[orig_idx])
                    copied["rerank_score"] = rank_item.get("relevance_score", 0)
                    copied["rerank_rank"] = len(ranked) + 1
                    ranked.append(copied)
            return {"items": ranked, "mode": "dashscope", "model": self.model}

        except Exception as exc:
            import logging
            logging.getLogger("app").warning(
                "DashScope rerank failed, falling back to passthrough: %s", exc
            )
            return self._passthrough(chunks, top_n)


rerank_client = RerankClient()
