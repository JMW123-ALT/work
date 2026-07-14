import pytest

from app.db.models.documents import Chunk, Document
from app.services.platform_services.retrieval import RetrievalService


class FakeCollection:
    def query(self, **kwargs):
        return {
            "ids": [["chunk-pg-id-1"]],
            "documents": [["向量库里的内容"]],
            "metadatas": [[{"chunk_id": "chunk-pg-id-1"}]],
            "distances": [[0.12]],
        }


class DimensionMismatchCollection:
    def query(self, **kwargs):
        raise ValueError("Collection expecting embedding with dimension of 1024, got 2560")


class FakeEmbedder:
    def embed_text(self, text: str):
        return {"type": "dense", "data": [1.0, 2.0, 3.0]}


class FakeReranker:
    def __init__(self, score: float = 0.92):
        self.score = score

    def rerank(self, query: str, items: list[dict], top_n: int):
        ranked = []
        for index, item in enumerate(items[:top_n], start=1):
            ranked.append({**item, "rerank_score": self.score, "rerank_rank": index})
        return {"items": ranked, "mode": "fake", "model": "fake-rerank"}


def make_document():
    return Document(
        id="doc-1",
        organization_id="org-1",
        source_id="src-1",
        title="秀洲区郊野公园概念方案",
        object_type="internal_doc",
        access_channel="web_upload",
        original_ref_uri="upload://park.pdf",
        modality="pdf",
    )


def make_chunk():
    return Chunk(
        id="chunk-pg-id-1",
        document_id="doc-1",
        document_version_id="version-1",
        chunk_id="legacy-src-chunk-0000",
        source_id="src-1",
        chunk_index=0,
        section_path="方案 / 第 1 页",
        content="PostgreSQL chunk 正文",
        modality="pdf",
        parser="langchain_pdf_page_splitter",
        page_number=1,
        asset_path="D:/assets/page-0001.jpg",
        asset_mime_type="image/jpeg",
        embedding_modality="pdf_page",
        content_hash="hash",
        vector_status="indexed",
    )


@pytest.mark.asyncio
async def test_v2_retrieval_returns_agent_ready_evidence_from_postgres_metadata():
    chunk = make_chunk()
    document = make_document()
    service = RetrievalService(
        session=None,
        collection=FakeCollection(),
        embedder=FakeEmbedder(),
        reranker=FakeReranker(score=0.92),
        chunk_loader=lambda ids: {"chunk-pg-id-1": (chunk, document)},
    )

    result = await service.search(
        {"query": "秀洲区郊野公园方案", "top_k": 3, "min_confidence": 0.7}
    )

    assert result["rerank"] == {"mode": "fake", "model": "fake-rerank"}
    assert result["blockedCount"] == 0
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["text"] == "PostgreSQL chunk 正文"
    assert item["source"] == "shujuku:src-1"
    assert item["culture_theme"] == "秀洲区郊野公园概念方案"
    assert item["confidence"] == 0.92
    assert item["metadata"]["chunk_id"] == "chunk-pg-id-1"
    assert item["metadata"]["legacy_chunk_id"] == "legacy-src-chunk-0000"
    assert item["metadata"]["page_number"] == 1
    assert item["metadata"]["asset_path"] == "D:/assets/page-0001.jpg"


@pytest.mark.asyncio
async def test_v2_retrieval_filters_by_min_confidence():
    service = RetrievalService(
        session=None,
        collection=FakeCollection(),
        embedder=FakeEmbedder(),
        reranker=FakeReranker(score=0.2),
        chunk_loader=lambda ids: {"chunk-pg-id-1": (make_chunk(), make_document())},
    )

    result = await service.search(
        {"query": "秀洲区郊野公园方案", "top_k": 3, "min_confidence": 0.7}
    )

    assert result["items"] == []


@pytest.mark.asyncio
async def test_v2_retrieval_reports_dimension_mismatch_clearly():
    service = RetrievalService(
        session=None,
        collection=DimensionMismatchCollection(),
        embedder=FakeEmbedder(),
        reranker=FakeReranker(score=0.2),
        chunk_loader=lambda ids: {},
    )

    with pytest.raises(ValueError, match="Chroma v2 collection dimension mismatch"):
        await service.search(
            {"query": "秀洲区郊野公园方案", "top_k": 3, "min_confidence": 0.7}
        )
