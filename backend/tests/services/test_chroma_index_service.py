from datetime import datetime

import pytest

from app.db.models.documents import Chunk
from app.services.platform_services.retrieval import ChromaIndexService


class FakeCollection:
    def __init__(self):
        self.upserts = []

    def upsert(self, *, ids, documents, metadatas, embeddings):
        self.upserts.append(
            {
                "ids": ids,
                "documents": documents,
                "metadatas": metadatas,
                "embeddings": embeddings,
            }
        )


class FakeEmbedder:
    model = "fake-embedding"

    def __init__(self):
        self.text_calls = []
        self.multimodal_calls = []

    def embed_text(self, text: str):
        self.text_calls.append(text)
        return {"type": "dense", "data": [1.0, 2.0, 3.0]}

    def embed_multimodal(self, text: str, *, image_path: str = "", mime_type: str = ""):
        self.multimodal_calls.append(
            {"text": text, "image_path": image_path, "mime_type": mime_type}
        )
        return {"type": "dense", "data": [4.0, 5.0, 6.0]}


def make_chunk(**overrides):
    values = {
        "id": "chunk-pg-id-1",
        "document_id": "doc-1",
        "document_version_id": "version-1",
        "chunk_id": "legacy-src-chunk-0000",
        "source_id": "src-1",
        "chunk_index": 0,
        "section_path": "章节",
        "content": "文创内容",
        "modality": "text",
        "parser": "fake",
        "page_number": 0,
        "asset_path": "",
        "asset_mime_type": "",
        "embedding_modality": "text",
        "content_hash": "hash",
        "vector_status": "pending",
    }
    values.update(overrides)
    return Chunk(**values)


@pytest.mark.asyncio
async def test_index_pending_chunks_upserts_to_chroma_with_postgres_chunk_id():
    collection = FakeCollection()
    embedder = FakeEmbedder()
    chunk = make_chunk()
    service = ChromaIndexService(
        session=None,
        collection=collection,
        embedder=embedder,
        pending_loader=lambda limit: [chunk],
    )

    result = await service.index_pending(limit=10)

    assert result["indexed"] == 1
    assert result["failed"] == 0
    assert collection.upserts[0]["ids"] == ["chunk-pg-id-1"]
    assert collection.upserts[0]["documents"] == ["文创内容"]
    assert collection.upserts[0]["metadatas"][0]["chunk_id"] == "chunk-pg-id-1"
    assert collection.upserts[0]["metadatas"][0]["legacy_chunk_id"] == "legacy-src-chunk-0000"
    assert chunk.vector_status == "indexed"
    assert chunk.embedding_model == "fake-embedding"
    assert isinstance(chunk.indexed_at, datetime)


@pytest.mark.asyncio
async def test_index_pending_chunks_uses_multimodal_embedding_when_asset_exists():
    collection = FakeCollection()
    embedder = FakeEmbedder()
    chunk = make_chunk(
        asset_path="D:/assets/page-0001.jpg",
        asset_mime_type="image/jpeg",
        embedding_modality="pdf_page",
    )
    service = ChromaIndexService(
        session=None,
        collection=collection,
        embedder=embedder,
        pending_loader=lambda limit: [chunk],
    )

    result = await service.index_pending(limit=10)

    assert result["indexed"] == 1
    assert embedder.multimodal_calls[0]["image_path"] == "D:/assets/page-0001.jpg"
    assert collection.upserts[0]["embeddings"] == [[4.0, 5.0, 6.0]]


@pytest.mark.asyncio
async def test_index_pending_chunks_marks_failed_chunk_when_embedding_fails():
    class BrokenEmbedder(FakeEmbedder):
        def embed_text(self, text: str):
            raise RuntimeError("embedding failed")

    collection = FakeCollection()
    chunk = make_chunk()
    service = ChromaIndexService(
        session=None,
        collection=collection,
        embedder=BrokenEmbedder(),
        pending_loader=lambda limit: [chunk],
    )

    result = await service.index_pending(limit=10)

    assert result["indexed"] == 0
    assert result["failed"] == 1
    assert collection.upserts == []
    assert chunk.vector_status == "failed"
