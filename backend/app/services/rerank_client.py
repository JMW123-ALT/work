"""
Rerank 客户端
- provider=passthrough / local / "" → 直接按向量检索分数排序（无需 API）
- provider=dashscope               → 阿里 DashScope gte-rerank

接口文档：https://help.aliyun.com/zh/dashscope/developer-reference/text-rerank
"""
import base64
import json
import mimetypes
from pathlib import Path

from app.core.config import settings

# DashScope rerank endpoint
_RERANK_PATH = "services/rerank/text-rerank/text-rerank"


def rerank_url(base_url: str) -> str:
    clean_base = (base_url or "https://dashscope.aliyuncs.com/api/v1").rstrip("/")
    if clean_base.endswith(_RERANK_PATH):
        return clean_base
    return f"{clean_base}/{_RERANK_PATH}"


def is_multimodal_rerank_model(model: str) -> bool:
    return "vl" in (model or "").lower() or "multimodal" in (model or "").lower()


def build_rerank_documents(chunks: list[dict], *, multimodal: bool) -> list:
    documents = []
    for chunk in chunks:
        text = chunk.get("content") or chunk.get("snippet") or chunk.get("chunk_content") or ""
        if not multimodal:
            documents.append(text)
            continue

        document: dict[str, str] = {"text": text or " "}
        asset_path = str(chunk.get("asset_path") or "")
        asset_url = str(chunk.get("asset_url") or "")
        if asset_url:
            document["image"] = asset_url
        elif asset_path and Path(asset_path).exists():
            path = Path(asset_path)
            mime_type = (
                str(chunk.get("asset_mime_type") or "")
                or mimetypes.guess_type(path.name)[0]
                or "image/png"
            )
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            document["image"] = f"data:{mime_type};base64,{encoded}"
        documents.append(document)
    return documents


class RerankClient:
    def __init__(self) -> None:
        self.provider = settings.rerank_provider
        self.model = settings.rerank_model or "qwen3-rerank"

    # ── 公共接口 ──────────────────────────────────────────────────

    def rerank(self, query: str, chunks: list[dict], top_n: int = 5) -> dict:
        if (
            self.provider == "dashscope"
            and settings.rerank_enabled
            and settings.rerank_api_key
        ):
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

        multimodal = is_multimodal_rerank_model(self.model)
        documents = build_rerank_documents(chunks, multimodal=multimodal)
        if not documents:
            return self._passthrough(chunks, top_n)

        payload = json.dumps(
            {
                "model": self.model,
                "input": {
                    "query": {"text": query} if multimodal else query,
                    "documents": documents,
                },
                "parameters": {"top_n": top_n, "return_documents": False},
            },
            ensure_ascii=False,
        ).encode("utf-8")

        req = urllib.request.Request(
            rerank_url(settings.rerank_base_url),
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
