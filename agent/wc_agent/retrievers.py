"""检索适配层。

Agent 不直接依赖某个具体数据库，只依赖 `Retriever.search()` 协议。
当前提供本地 Mock、Chroma 适配器和未来数据库占位，后续可以新增同事
`shujuku` 项目的 HTTP/SQLite 适配器。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Protocol

import chromadb
import httpx

from .model_services import EmbeddingClient, RerankClient
from .settings import Settings, get_settings
from .state import Evidence


class Retriever(Protocol):
    """所有检索器必须实现的最小接口。"""

    def search(self, query: str, n_results: int = 5) -> list[Evidence]:
        ...


class MockKnowledgeRetriever:
    """本地 JSONL 检索器。

    在真实数据库尚未接入时，用它模拟“有史料再生成”的 RAG 流程。
    """

    def __init__(self, path: Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.path = path or self.settings.mock_knowledge_path
        self.items = self._load_items()

    def search(self, query: str, n_results: int = 5) -> list[Evidence]:
        """按关键词重合度做一个轻量相关性打分。"""

        query_terms = tokenize(query)
        scored: list[tuple[float, Evidence]] = []
        for item in self.items:
            haystack = " ".join(
                [
                    item.text,
                    item.source,
                    item.category,
                    item.culture_theme,
                ]
            )
            hay_terms = tokenize(haystack)
            overlap = len(query_terms & hay_terms)
            phrase_bonus = 1 if any(term and term in haystack for term in query_terms) else 0
            confidence = min(0.98, 0.45 + overlap * 0.16 + phrase_bonus * 0.12)
            if confidence >= self.settings.min_confidence:
                scored.append((confidence, item.model_copy(update={"confidence": confidence})))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[:n_results]]

    def _load_items(self) -> list[Evidence]:
        """从 JSONL 样例库加载 Evidence。"""

        if not self.path.exists():
            return []
        items: list[Evidence] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            items.append(Evidence.model_validate(json.loads(line)))
        return items


class ChromaRetriever:
    """Chroma 检索适配器。

    这个类只负责连接 collection 并把返回结果标准化为 `Evidence`。
    真正的入库、embedding 和 collection 管理由数据库项目负责。
    """

    def __init__(
        self,
        path: Path | str | None = None,
        collection_name: str | None = None,
        settings: Settings | None = None,
        embedding_client: EmbeddingClient | None = None,
        rerank_client: RerankClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.path = str(path or self.settings.chroma_path)
        self.collection_name = collection_name or self.settings.chroma_collection
        self.embedding_client = embedding_client or EmbeddingClient(self.settings)
        self.rerank_client = rerank_client or RerankClient(self.settings)
        self.client = chromadb.PersistentClient(path=self.path)
        self.collection = self.client.get_or_create_collection(self.collection_name)

    def search(self, query: str, n_results: int = 5) -> list[Evidence]:
        """查询 Chroma collection，并按置信度阈值过滤结果。"""

        if self.collection.count() == 0:
            return []

        initial_n_results = max(n_results * 4, n_results) if self.settings.rerank_enabled else n_results
        query_embedding = self.embedding_client.embed_text(query)
        if query_embedding:
            result = self.collection.query(query_embeddings=[query_embedding], n_results=initial_n_results)
        else:
            result = self.collection.query(query_texts=[query], n_results=initial_n_results)
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        evidence: list[Evidence] = []
        for text, metadata, distance in zip(documents, metadatas, distances, strict=False):
            confidence = distance_to_confidence(distance)
            if confidence < self.settings.min_confidence:
                continue
            metadata = metadata or {}
            evidence.append(chroma_result_to_evidence(str(text), metadata, confidence))
        return self.rerank_client.rerank(query, evidence, top_n=n_results)


class FutureDatabaseRetriever:
    """同事数据库仓库的占位适配器。

    现在先明确边界，等 `shujuku` 服务接口稳定后再替换为真实实现。
    """

    def search(self, query: str, n_results: int = 5) -> list[Evidence]:
        raise NotImplementedError(
            "Real database integration is intentionally left open. "
            "Implement this adapter after pulling the database repo from GitHub."
        )


class ShujukuHttpRetriever:
    """通过同仓库 backend 的 `/api/v1/search` 读取真实知识库数据。"""

    def __init__(self, settings: Settings | None = None, http_client: httpx.Client | None = None) -> None:
        self.settings = settings or get_settings()
        self.http_client = http_client

    def search(self, query: str, n_results: int = 5) -> list[Evidence]:
        """调用 backend search 接口，并把结果转换为 Agent Evidence。"""

        payload = {
            "query": query,
            "user_type": self.settings.shujuku_user_type,
            "top_k": n_results,
            "retrieval_top_k": max(n_results * 4, n_results),
            "min_confidence": self.settings.min_confidence,
        }
        try:
            data = self._post_search(payload)
        except (httpx.HTTPError, ValueError, TypeError):
            return []

        evidence: list[Evidence] = []
        for item in data.get("items", []):
            parsed = backend_search_item_to_evidence(item)
            if parsed.confidence >= self.settings.min_confidence:
                evidence.append(parsed)
        return evidence[:n_results]

    def _post_search(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.http_client is not None:
            response = self.http_client.post(self.settings.shujuku_search_url, json=payload)
        else:
            with httpx.Client(timeout=self.settings.shujuku_search_timeout) as client:
                response = client.post(self.settings.shujuku_search_url, json=payload)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("backend search response must be a JSON object")
        return data


def backend_search_item_to_evidence(item: dict[str, Any]) -> Evidence:
    """把 backend `/api/v1/search` 的标准 item 转为 Agent Evidence。"""

    return Evidence(
        text=str(item.get("text") or ""),
        source=str(item.get("source") or "shujuku:unknown"),
        category=str(item.get("category") or "unknown"),
        culture_theme=str(item.get("culture_theme") or "unknown"),
        confidence=float(item.get("confidence") or 0.0),
        copyright_status=str(item.get("copyright_status") or "unknown"),
        risk_level=str(item.get("risk_level") or "low"),
    )


def get_default_retriever(settings: Settings | None = None) -> Retriever:
    """根据配置选择默认检索器。"""

    active_settings = settings or get_settings()
    provider = active_settings.retriever_provider
    if provider in {"shujuku", "backend", "http"}:
        return ShujukuHttpRetriever(settings=active_settings)
    if provider == "chroma":
        return ChromaRetriever(settings=active_settings)
    if provider == "mock":
        return MockKnowledgeRetriever(settings=active_settings)
    raise ValueError(f"Unsupported RETRIEVER_PROVIDER: {provider}")


def distance_to_confidence(distance: float | int | None) -> float:
    """把 Chroma distance 粗略转换为 0-1 置信度。"""

    if distance is None:
        return 0.0
    # Chroma distances vary by embedding function. This conservative transform
    # keeps the Agent threshold logic stable while the real DB adapter is pending.
    return max(0.0, min(1.0, 1.0 - float(distance)))


def chroma_result_to_evidence(document: str, metadata: dict[str, Any], confidence: float) -> Evidence:
    """把同事 Chroma 1.4.4 字段转换成 Agent 使用的 Evidence。

    同事约定：id 使用 chunk_id，document 是 chunk 正文，metadata 中包含
    chunk_id/source_id/title/object_type/permission_level 等业务字段。
    """

    title = str(metadata.get("title") or "")
    section_path = str(metadata.get("section_path") or "")
    source_id = str(metadata.get("source_id") or metadata.get("chunk_id") or "unknown")
    object_type = str(metadata.get("object_type") or metadata.get("category") or "unknown")
    permission_level = str(metadata.get("permission_level") or "")

    return Evidence(
        text=document,
        source=f"shujuku:{source_id}",
        category=object_type,
        culture_theme=title or section_path or "unknown",
        copyright_status=permission_to_copyright_status(permission_level),
        risk_level=permission_to_risk_level(permission_level),
        confidence=confidence,
    )


def permission_to_copyright_status(permission_level: str) -> str:
    """把知识库权限字段转换为 Agent 的版权/授权状态。"""

    if permission_level == "public":
        return "public_domain"
    if permission_level in {"free", "paid", "internal"}:
        return "authorized"
    return "unknown"


def permission_to_risk_level(permission_level: str) -> str:
    """把权限等级粗略映射成风险等级，供后置风控使用。"""

    if permission_level in {"internal", "restricted"}:
        return "medium"
    return "low"


def tokenize(text: str) -> set[str]:
    """给 Mock 检索使用的简易分词。

    这里故意保持简单，真实语义检索会交给 embedding/向量库处理。
    """

    parts = re.split(r"[\s,，。；;、/：:（）()《》\"'“”]+", text.lower())
    terms = {part for part in parts if part}
    for keyword in ["敦煌", "藻井", "纹样", "唐代", "保温杯", "非遗", "策展", "小红书", "抖音", "国潮"]:
        if keyword.lower() in text.lower():
            terms.add(keyword.lower())
    return terms
