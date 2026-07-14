import hashlib
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.documents import Chunk, Document
from app.services.permissions import permission_notice
from app.services.rag_service import _to_agent_search_item
from app.services.embedding_client import embedding_client
from app.services.rerank_client import rerank_client


class ChromaIndexService:
    """Service boundary for future PostgreSQL -> Chroma v2 indexing."""

    def __init__(
        self,
        session: AsyncSession | None,
        *,
        collection: Any | None = None,
        embedder: Any | None = None,
        pending_loader: Callable[[int], list[Chunk]] | None = None,
    ) -> None:
        self.session = session
        self.collection_name = settings.chroma_collection_v2
        self.collection = collection
        self.embedder = embedder or embedding_client
        self.pending_loader = pending_loader

    async def chunks_pending_index(self, limit: int = 100) -> list[Chunk]:
        result = await self.session.execute(
            select(Chunk)
            .where(Chunk.vector_status.in_(["pending", "failed"]))
            .order_by(Chunk.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    def embed_chunk(self, chunk: Chunk) -> dict:
        text = chunk.content
        if chunk.asset_path:
            return self.embedder.embed_multimodal(
                text,
                image_path=chunk.asset_path,
                mime_type=chunk.asset_mime_type,
            )
        return self.embedder.embed_text(text)

    async def index_pending(self, limit: int = 100) -> dict[str, Any]:
        chunks = (
            self.pending_loader(limit)
            if self.pending_loader is not None
            else await self.chunks_pending_index(limit)
        )
        collection = self.collection or self._get_or_create_collection()
        indexed = 0
        failed = 0
        errors: list[dict[str, str]] = []

        for chunk in chunks:
            try:
                vector = self.embed_chunk(chunk)
                collection.upsert(
                    ids=[chunk.id],
                    documents=[chunk.content],
                    metadatas=[self._chunk_metadata(chunk)],
                    embeddings=[_to_chroma_embedding(vector)],
                )
                chunk.vector_status = "indexed"
                chunk.embedding_model = getattr(
                    self.embedder,
                    "model",
                    settings.embedding_model,
                )
                chunk.embedding_version = "v2"
                chunk.indexed_at = datetime.now(timezone.utc)
                indexed += 1
            except Exception as exc:
                chunk.vector_status = "failed"
                failed += 1
                errors.append({"chunk_id": chunk.id, "error": str(exc)})

        return {
            "collection": self.collection_name,
            "indexed": indexed,
            "failed": failed,
            "errors": errors,
        }

    def _get_or_create_collection(self):
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError(
                "chromadb is not installed. Run `pip install -r backend/requirements.txt`."
            ) from exc
        client = chromadb.PersistentClient(path=str(settings.chroma_path))
        return client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": settings.chroma_distance_space},
        )

    def _chunk_metadata(self, chunk: Chunk) -> dict[str, str | int]:
        raw = {
            "chunk_id": chunk.id,
            "legacy_chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "document_version_id": chunk.document_version_id,
            "source_id": chunk.source_id,
            "chunk_index": int(chunk.chunk_index),
            "section_path": chunk.section_path,
            "modality": chunk.modality,
            "parser": chunk.parser,
            "page_number": int(chunk.page_number or 0),
            "asset_path": chunk.asset_path,
            "asset_mime_type": chunk.asset_mime_type,
            "embedding_modality": chunk.embedding_modality,
            "content_hash": chunk.content_hash,
            "vector_status": "indexed",
        }
        return {key: _metadata_value(value) for key, value in raw.items()}


class RetrievalService:
    """PostgreSQL metadata + Chroma recall + rerank service boundary."""

    def __init__(
        self,
        session: AsyncSession | None,
        *,
        collection: Any | None = None,
        embedder: Any | None = None,
        reranker: Any | None = None,
        chunk_loader: Callable[[list[str]], dict[str, tuple[Chunk, Document]]] | None = None,
    ) -> None:
        self.session = session
        self.collection_name = settings.chroma_collection_v2
        self.collection = collection
        self.embedder = embedder or embedding_client
        self.reranker = reranker or rerank_client
        self.chunk_loader = chunk_loader

    def rerank_items(self, query: str, items: list[dict], top_n: int) -> dict:
        return self.reranker.rerank(query, items, top_n=top_n)

    async def search(self, payload: dict) -> dict:
        query = (payload.get("query") or "").strip()
        if not query:
            raise ValueError("query is required")

        top_k = int(payload.get("top_k", 5))
        retrieval_top_k = int(payload.get("retrieval_top_k") or max(top_k * 4, top_k))
        min_confidence = float(payload.get("min_confidence", 0.7))

        collection = self.collection or ChromaIndexService(self.session)._get_or_create_collection()
        query_vector = self.embedder.embed_text(query)
        try:
            result = collection.query(
                query_embeddings=[_to_chroma_embedding(query_vector)],
                n_results=retrieval_top_k,
            )
        except Exception as exc:
            if "expecting embedding with dimension" in str(exc).lower():
                raise ValueError(
                    "Chroma v2 collection dimension mismatch. "
                    "Reset wenchuang_knowledge_v2 and run vector indexing again "
                    "with the current embedding model."
                ) from exc
            raise
        raw_items = await self._format_results(result)
        reranked = self.rerank_items(query, raw_items, top_n=top_k)
        items = [
            item
            for item in (_to_agent_search_item(raw_item) for raw_item in reranked["items"])
            if item["confidence"] >= min_confidence
        ]
        return {
            "items": items,
            "blockedCount": 0,
            "permissionNotice": permission_notice(0),
            "rerank": {"mode": reranked["mode"], "model": reranked["model"]},
        }

    async def _format_results(self, result: dict) -> list[dict]:
        ids = (result.get("ids") or [[]])[0] or []
        documents = (result.get("documents") or [[]])[0] or []
        metadatas = (result.get("metadatas") or [[]])[0] or []
        distances = (result.get("distances") or [[]])[0] or []
        records = await self._chunks_by_ids([str(item) for item in ids])

        items = []
        for index, chunk_id in enumerate(ids):
            chunk_key = str(chunk_id)
            pair = records.get(chunk_key)
            if not pair:
                continue
            chunk, document = pair
            metadata = dict(metadatas[index] or {}) if index < len(metadatas) else {}
            score = _score_from_distance(distances[index] if index < len(distances) else None)
            content = chunk.content or (documents[index] if index < len(documents) else "")
            items.append(
                {
                    "chunk_id": chunk.id,
                    "legacy_chunk_id": chunk.chunk_id,
                    "source_id": chunk.source_id,
                    "chunk_index": int(chunk.chunk_index),
                    "chunk_section_path": chunk.section_path,
                    "chunk_content": content,
                    "content": content,
                    "snippet": content[:180],
                    "title": document.title,
                    "object_type": document.object_type,
                    "permission_level": metadata.get("permission_level", "public"),
                    "access_channel": document.access_channel,
                    "original_ref_uri": document.original_ref_uri,
                    "section_path": chunk.section_path,
                    "modality": chunk.modality,
                    "parser": chunk.parser,
                    "page_number": int(chunk.page_number or 0),
                    "asset_path": chunk.asset_path,
                    "asset_mime_type": chunk.asset_mime_type,
                    "embedding_modality": chunk.embedding_modality,
                    "file_name": metadata.get("file_name", ""),
                    "mime_type": metadata.get("mime_type", ""),
                    "file_size": int(metadata.get("file_size") or 0),
                    "chunk_count": int(metadata.get("chunk_count") or 0),
                    "extraction_status": metadata.get("extraction_status", "parsed"),
                    "runtime": int(metadata.get("runtime") or 0),
                    "created_at": str(chunk.created_at or ""),
                    "updated_at": str(chunk.updated_at or ""),
                    "score": round(score, 4),
                }
            )
        return items

    async def _chunks_by_ids(self, chunk_ids: list[str]) -> dict[str, tuple[Chunk, Document]]:
        if self.chunk_loader is not None:
            return self.chunk_loader(chunk_ids)
        if not chunk_ids:
            return {}
        result = await self.session.execute(
            select(Chunk, Document)
            .join(Document, Chunk.document_id == Document.id)
            .where(Chunk.id.in_(chunk_ids))
        )
        return {chunk.id: (chunk, document) for chunk, document in result.all()}


def _to_chroma_embedding(vector: dict) -> list[float]:
    if vector.get("type") == "dense":
        return _non_zero_vector([float(value) for value in vector.get("data", [])])

    sparse = vector.get("data", vector)
    dimension = max(16, int(settings.chroma_local_embedding_dimension or 1024))
    dense = [0.0] * dimension
    if isinstance(sparse, dict):
        for token, weight in sparse.items():
            digest = hashlib.blake2b(str(token).encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest, "big") % dimension
            sign = 1.0 if digest[0] % 2 == 0 else -1.0
            dense[index] += sign * float(weight)
    return _non_zero_vector(dense, normalize=True)


def _non_zero_vector(values: list[float], normalize: bool = False) -> list[float]:
    if not values:
        return [1.0] + [0.0] * 15
    if normalize:
        norm = sum(value * value for value in values) ** 0.5
        if norm > 0:
            values = [value / norm for value in values]
    if any(value != 0 for value in values):
        return values
    values[0] = 1.0
    return values


def _metadata_value(value):
    if value is None:
        return ""
    if isinstance(value, bool | int | float | str):
        return value
    return str(value)


def _score_from_distance(distance: Any) -> float:
    if distance is None:
        return 0.0
    try:
        value = float(distance)
    except (TypeError, ValueError):
        return 0.0
    if settings.chroma_distance_space == "cosine":
        return max(0.0, 1.0 - value)
    return 1.0 / (1.0 + max(0.0, value))
