"""
Embedding 客户端
支持两种 DashScope 接口：

  provider=local
    → 本地 ngram 占位向量（无需 API key）

  provider=dashscope，模型名含 "vl" 或 "multimodal"（如 qwen3-vl-embedding）
    → 原生多模态接口
      POST https://dashscope.aliyuncs.com/api/v1/services/embeddings/
               multimodal-embedding/multimodal-embedding
      body: {"model": "...", "input": {"contents": [{"text": "..."}]},
             "parameters": {"enable_fusion": true}}

  provider=dashscope，其余模型（如 text-embedding-v3）
    → OpenAI 兼容接口
      POST https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings
      body: {"model": "...", "input": "...", "encoding_format": "float"}

向量格式（供 vector_store 使用）：
  {"type": "sparse", "data": {token: weight}}   本地占位
  {"type": "dense",  "data": [float, ...]}       DashScope 真实向量
"""
import json
import re
from collections import Counter

from app.core.config import settings

# ── 接口地址 ─────────────────────────────────────────────────────
_COMPAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
_MULTIMODAL_PATH = "services/embeddings/multimodal-embedding/multimodal-embedding"


def _is_multimodal_model(model: str) -> bool:
    """通过模型名判断是否走原生多模态接口。"""
    m = model.lower()
    return "vl" in m or "multimodal" in m


def multimodal_embedding_url(base_url: str) -> str:
    """根据配置生成 qwen3-vl-embedding 原生多模态 endpoint。"""

    clean_base = (base_url or "https://dashscope.aliyuncs.com/api/v1").rstrip("/")
    if clean_base.endswith(_MULTIMODAL_PATH):
        return clean_base
    return f"{clean_base}/{_MULTIMODAL_PATH}"


class EmbeddingClient:
    def __init__(self) -> None:
        self.provider = settings.embedding_provider
        self.model = settings.embedding_model or "text-embedding-v3"

    # ── 公共接口 ──────────────────────────────────────────────────

    def embed_text(self, text: str) -> dict:
        """返回向量 dict，供 vector_store 序列化使用。

        格式：
          {"type": "sparse", "data": {...}}  — 本地占位
          {"type": "dense",  "data": [...]}  — DashScope 真实向量
        """
        if self.provider not in ("", "local") and settings.embedding_api_key:
            if _is_multimodal_model(self.model):
                return self._embed_multimodal(text)
            return self._embed_compat(text)
        return self._embed_locally(text)

    # ── 本地占位 ──────────────────────────────────────────────────

    def _embed_locally(self, text: str) -> dict:
        normalized = (text or "").lower()
        vector: Counter = Counter()

        for token in re.findall(r"[A-Za-z0-9_]+", normalized):
            vector[token] += 2

        chinese_chars = re.findall(r"[一-鿿]", normalized)
        for char in chinese_chars:
            vector[char] += 1

        compact_cn = "".join(chinese_chars)
        for size, weight in ((2, 3), (3, 4), (4, 4)):
            for idx in range(max(0, len(compact_cn) - size + 1)):
                vector[compact_cn[idx : idx + size]] += weight

        return {"type": "sparse", "data": dict(vector)}

    # ── DashScope 原生多模态接口（qwen3-vl-embedding 等）─────────

    def _embed_multimodal(self, text: str) -> dict:
        """调用 DashScope 原生多模态 embedding 接口。

        文档示例（多图+视频+文本融合向量）：
          POST /api/v1/services/embeddings/multimodal-embedding/multimodal-embedding
          {
            "model": "qwen3-vl-embedding",
            "input": {
              "contents": [
                {"text": "商品描述文本"},
                {"image": "https://..."},
                {"video":  "https://..."}
              ]
            },
            "parameters": {"enable_fusion": true}
          }

        纯文本入库时只传 text 内容即可，其余字段不变。
        """
        import urllib.request

        payload = json.dumps(
            {
                "model": self.model,
                "input": {
                    "contents": [{"text": (text or "").strip() or " "}]
                },
                "parameters": {"enable_fusion": True},
            },
            ensure_ascii=False,
        ).encode("utf-8")

        req = urllib.request.Request(
            multimodal_embedding_url(settings.embedding_base_url),
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.embedding_api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            # 响应格式：{"output": {"embeddings": [{"index": 0, "embedding": [...]}]}}
            vector: list[float] = result["output"]["embeddings"][0]["embedding"]
            return {"type": "dense", "data": vector}
        except Exception as exc:
            import logging
            logging.getLogger("app").warning(
                "DashScope multimodal embedding failed, falling back to local: %s", exc
            )
            return self._embed_locally(text)

    # ── DashScope OpenAI 兼容接口（text-embedding-v3 等）─────────

    # text-embedding-v3 单次最大 8192 tokens；保守取 6000 中文字符（约 4000 tokens）
    _COMPAT_MAX_CHARS = 6000

    def _embed_compat(self, text: str) -> dict:
        """调用 DashScope OpenAI 兼容 embedding 接口。

        会在发送前：
          1. 截断超长文本（>_COMPAT_MAX_CHARS 字符），防止 400 token-limit 错误；
          2. 若清洗后为空字符串，直接走本地占位向量。
        """
        import urllib.error
        import urllib.request

        clean = (text or "").strip()
        if not clean:
            return self._embed_locally(text)
        if len(clean) > self._COMPAT_MAX_CHARS:
            clean = clean[: self._COMPAT_MAX_CHARS]

        payload = json.dumps(
            {"model": self.model, "input": clean, "encoding_format": "float"},
            ensure_ascii=False,
        ).encode("utf-8")

        req = urllib.request.Request(
            _COMPAT_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.embedding_api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            vector: list[float] = result["data"][0]["embedding"]
            return {"type": "dense", "data": vector}
        except urllib.error.HTTPError as exc:
            # 读取响应体，方便排查 400/401/429 等具体原因
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body = "<unreadable>"
            import logging
            logging.getLogger("app").warning(
                "DashScope embedding failed, falling back to local: %s — %s", exc, body
            )
            return self._embed_locally(text)
        except Exception as exc:
            import logging
            logging.getLogger("app").warning(
                "DashScope embedding failed, falling back to local: %s", exc
            )
            return self._embed_locally(text)


embedding_client = EmbeddingClient()
