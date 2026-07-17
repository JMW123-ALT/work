from datetime import datetime, timezone

import pytest

from app.db.models.documents import Document, DocumentFile, DocumentVersion
from app.db.models.governance import DocumentGovernance
from app.services.platform_services.documents import DocumentLibraryService


class FakeDocumentLibraryRepository:
    async def list_document_summaries(self, organization_id: str, limit: int = 100):
        assert organization_id == "org-1"
        assert limit == 100
        document = Document(
            id="doc-1",
            organization_id="org-1",
            source_id="src-1",
            title="资源库资料",
            object_type="planning",
            access_channel="web_upload",
            original_ref_uri="upload://sample.pdf",
            modality="pdf",
            file_sha256="abc",
            content_sha256="def",
            created_at=datetime(2026, 7, 16, 1, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 7, 16, 2, 0, tzinfo=timezone.utc),
        )
        version = DocumentVersion(
            id="version-1",
            document_id="doc-1",
            version=1,
            title="资源库资料",
            content="正文",
            parser="chunking_client",
            extraction_status="parsed",
        )
        file = DocumentFile(
            id="file-1",
            document_id="doc-1",
            document_version_id="version-1",
            file_name="sample.pdf",
            file_path="backend/data/uploads/sample.pdf",
            mime_type="application/pdf",
            file_size=1234,
            file_sha256="abc",
        )
        governance = DocumentGovernance(
            document_id="doc-1",
            confidentiality_level="public",
        )
        return [(document, version, file, governance, 3)]


@pytest.mark.asyncio
async def test_document_library_lists_frontend_ready_postgres_documents():
    service = DocumentLibraryService(
        session=None,
        documents=FakeDocumentLibraryRepository(),
    )

    result = await service.list_documents("org-1")

    assert result == [
        {
            "source_id": "src-1",
            "title": "资源库资料",
            "object_type": "planning",
            "permission_level": "public",
            "access_channel": "web_upload",
            "original_ref_uri": "upload://sample.pdf",
            "section_path": "资源库资料",
            "modality": "pdf",
            "file_name": "sample.pdf",
            "file_path": "backend/data/uploads/sample.pdf",
            "mime_type": "application/pdf",
            "file_size": 1234,
            "chunk_count": 3,
            "extraction_status": "parsed",
            "content": "正文",
            "created_at": "2026-07-16T01:00:00+00:00",
            "updated_at": "2026-07-16T02:00:00+00:00",
            "runtime": 1,
        }
    ]
