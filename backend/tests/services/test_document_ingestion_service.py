from pathlib import Path

import pytest

from app.db.models.documents import Document
from app.services.platform_services.documents import DocumentIngestionService


class FakeDocumentRepository:
    def __init__(self, organization_exists: bool | None = None):
        self._organization_exists = organization_exists
        self.by_source_id = {}
        self.by_file_sha256 = {}
        self.documents = []
        self.versions = []
        self.files = []
        self.chunks = []

    async def organization_exists(self, organization_id: str):
        if self._organization_exists is None:
            return True
        return self._organization_exists

    async def get_by_source_id(self, organization_id: str, source_id: str):
        return self.by_source_id.get((organization_id, source_id))

    async def get_by_file_sha256(
        self,
        organization_id: str,
        project_id: str | None,
        file_sha256: str,
    ):
        return self.by_file_sha256.get((organization_id, project_id, file_sha256))

    async def add(self, item):
        self.documents.append(item)
        self.by_source_id[(item.organization_id, item.source_id)] = item
        if item.file_sha256:
            self.by_file_sha256[(item.organization_id, item.project_id, item.file_sha256)] = item
        return item

    async def add_version(self, version):
        self.versions.append(version)
        return version

    async def add_file(self, file):
        self.files.append(file)
        return file

    async def replace_chunks(self, document_version_id: str, chunks: list):
        self.chunks = [chunk for chunk in self.chunks if chunk.document_version_id != document_version_id]
        self.chunks.extend(chunks)
        return chunks


class FakeChunker:
    def extract_placeholder(self, file_path: Path, mime_type: str, description: str = ""):
        return {
            "modality": "text",
            "content": description or file_path.read_text(encoding="utf-8"),
            "extraction_status": "parsed",
        }

    def chunk_document(
        self,
        *,
        source_id: str,
        title: str,
        content: str,
        modality: str,
        section_path: str = "",
        file_path: str = "",
        mime_type: str = "",
    ):
        return [
            {
                "chunk_id": f"{source_id}-chunk-0000",
                "source_id": source_id,
                "chunk_index": 0,
                "section_path": section_path or title,
                "content": content,
                "modality": modality,
                "parser": "fake",
                "embedding_modality": "text",
            }
        ]


@pytest.mark.asyncio
async def test_create_text_document_writes_version_and_chunks():
    repository = FakeDocumentRepository()
    service = DocumentIngestionService(
        session=None,
        documents=repository,
        chunker=FakeChunker(),
    )

    result = await service.create_text_document(
        organization_id="org-1",
        source_id="src-1",
        title="测试资料",
        content="第一段内容",
    )

    assert result["duplicate"] is False
    assert result["chunk_count"] == 1
    assert len(repository.documents) == 1
    assert len(repository.versions) == 1
    assert len(repository.chunks) == 1
    assert repository.documents[0].content_sha256


@pytest.mark.asyncio
async def test_create_text_document_rejects_unknown_organization():
    repository = FakeDocumentRepository(organization_exists=False)
    service = DocumentIngestionService(
        session=None,
        documents=repository,
        chunker=FakeChunker(),
    )

    with pytest.raises(ValueError, match="organization_id does not exist"):
        await service.create_text_document(
            organization_id="missing-org",
            source_id="src-1",
            title="测试资料",
            content="第一段内容",
        )


@pytest.mark.asyncio
async def test_create_file_document_writes_file_version_and_chunks(tmp_path):
    repository = FakeDocumentRepository()
    service = DocumentIngestionService(
        session=None,
        documents=repository,
        chunker=FakeChunker(),
        upload_dir=tmp_path,
    )

    result = await service.create_file_document(
        organization_id="org-1",
        file_name="方案.txt",
        file_bytes="公园方案内容".encode("utf-8"),
        mime_type="text/plain",
        title="公园方案",
    )

    assert result["duplicate"] is False
    assert result["chunk_count"] == 1
    assert len(repository.documents) == 1
    assert len(repository.versions) == 1
    assert len(repository.files) == 1
    assert len(repository.chunks) == 1
    assert Path(repository.files[0].file_path).exists()
    assert repository.documents[0].file_sha256


@pytest.mark.asyncio
async def test_create_file_document_reuses_existing_file_hash(tmp_path):
    repository = FakeDocumentRepository()
    existing = Document(
        organization_id="org-1",
        project_id=None,
        source_id="src-existing",
        title="已有资料",
        file_sha256="placeholder",
    )
    service = DocumentIngestionService(
        session=None,
        documents=repository,
        chunker=FakeChunker(),
        upload_dir=tmp_path,
    )

    first = await service.create_file_document(
        organization_id="org-1",
        file_name="方案.txt",
        file_bytes=b"same content",
        mime_type="text/plain",
        title="公园方案",
    )
    repository.by_file_sha256[
        ("org-1", None, repository.documents[0].file_sha256)
    ] = existing

    second = await service.create_file_document(
        organization_id="org-1",
        file_name="方案-copy.txt",
        file_bytes=b"same content",
        mime_type="text/plain",
        title="公园方案副本",
    )

    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert second["document_id"] == existing.id
    assert len(repository.documents) == 1
    assert len(repository.chunks) == 1
