import hashlib
import re
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.documents import Chunk, Document, DocumentFile, DocumentVersion
from app.repositories.documents import DocumentRepository
from app.services.chunking_client import chunking_client


class DocumentIngestionService:
    """PostgreSQL v2 ingestion coordinator.

    This service reuses the existing parser and chunker. It intentionally does
    not call Embedding or Chroma; vector indexing is a separate service/task.
    """

    def __init__(
        self,
        session: AsyncSession | None,
        *,
        documents: Any | None = None,
        chunker: Any | None = None,
        upload_dir: Path | None = None,
    ) -> None:
        self.session = session
        self.documents = documents or DocumentRepository(session)
        self.chunker = chunker or chunking_client
        self.upload_dir = upload_dir or settings.upload_dir

    async def create_text_document(
        self,
        *,
        organization_id: str,
        title: str,
        content: str,
        source_id: str,
        project_id: str | None = None,
        modality: str = "text",
    ) -> dict[str, Any]:
        await self._ensure_organization_exists(organization_id)
        content_sha256 = _hash_text(content)
        existing = await self.documents.get_by_source_id(organization_id, source_id)
        if existing:
            return _result(existing, duplicate=True, chunk_count=0)

        document = Document(
            organization_id=organization_id,
            project_id=project_id,
            source_id=source_id,
            title=title,
            modality=modality,
            content_sha256=content_sha256,
        )
        await self.documents.add(document)

        version = DocumentVersion(
            document_id=document.id,
            version=1,
            title=title,
            content=content,
            content_sha256=content_sha256,
            parser="manual_text",
            extraction_status="parsed",
        )
        await self.documents.add_version(version)

        chunk_rows = self._build_chunks(
            document=document,
            version=version,
            source_id=source_id,
            title=title,
            content=content,
            modality=modality,
            section_path=title,
        )
        await self.documents.replace_chunks(version.id, chunk_rows)
        return _result(
            document,
            version_id=version.id,
            duplicate=False,
            chunk_count=len(chunk_rows),
        )

    async def create_file_document(
        self,
        *,
        organization_id: str,
        file_name: str,
        file_bytes: bytes,
        mime_type: str = "",
        title: str | None = None,
        source_id: str | None = None,
        project_id: str | None = None,
        object_type: str = "internal_doc",
        access_channel: str = "web_upload",
        description: str = "",
    ) -> dict[str, Any]:
        await self._ensure_organization_exists(organization_id)
        file_sha256 = _hash_bytes(file_bytes)
        existing = await self.documents.get_by_file_sha256(
            organization_id,
            project_id,
            file_sha256,
        )
        if existing:
            return _result(existing, duplicate=True, chunk_count=0)

        source_id = source_id or f"src-file-{file_sha256[:12]}"
        safe_name = _safe_file_name(file_name)
        stored_name = f"{source_id}-{safe_name}"
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = self.upload_dir / stored_name
        file_path.write_bytes(file_bytes)

        extracted = self.chunker.extract_placeholder(file_path, mime_type, description)
        content = extracted["content"]
        content_sha256 = _hash_text(content)
        document_title = (title or Path(file_name).stem or "Untitled").strip()

        document = Document(
            organization_id=organization_id,
            project_id=project_id,
            source_id=source_id,
            title=document_title,
            object_type=object_type,
            access_channel=access_channel,
            original_ref_uri=f"upload://{stored_name}",
            modality=extracted["modality"],
            file_sha256=file_sha256,
            content_sha256=content_sha256,
        )
        await self.documents.add(document)

        version = DocumentVersion(
            document_id=document.id,
            version=1,
            title=document_title,
            content=content,
            content_sha256=content_sha256,
            parser="chunking_client",
            extraction_status=extracted["extraction_status"],
            metadata_json={"file_name": file_name},
        )
        await self.documents.add_version(version)

        file_row = DocumentFile(
            document_id=document.id,
            document_version_id=version.id,
            file_name=file_name,
            file_path=str(file_path),
            mime_type=mime_type,
            file_size=len(file_bytes),
            file_sha256=file_sha256,
            file_role="original",
        )
        await self.documents.add_file(file_row)

        chunk_rows = self._build_chunks(
            document=document,
            version=version,
            source_id=source_id,
            title=document_title,
            content=content,
            modality=extracted["modality"],
            section_path=document_title,
            file_path=str(file_path),
            mime_type=mime_type,
        )
        await self.documents.replace_chunks(version.id, chunk_rows)
        return _result(
            document,
            version_id=version.id,
            file_id=file_row.id,
            duplicate=False,
            chunk_count=len(chunk_rows),
        )

    def _build_chunks(
        self,
        *,
        document: Document,
        version: DocumentVersion,
        source_id: str,
        title: str,
        content: str,
        modality: str,
        section_path: str,
        file_path: str = "",
        mime_type: str = "",
    ) -> list[Chunk]:
        chunks = self.chunker.chunk_document(
            source_id=source_id,
            title=title,
            content=content,
            modality=modality,
            section_path=section_path,
            file_path=file_path,
            mime_type=mime_type,
        )
        return [
            Chunk(
                document_id=document.id,
                document_version_id=version.id,
                chunk_id=chunk["chunk_id"],
                source_id=source_id,
                chunk_index=int(chunk["chunk_index"]),
                section_path=chunk.get("section_path", title),
                content=chunk["content"],
                modality=chunk.get("modality", modality),
                parser=chunk.get("parser", ""),
                page_number=int(chunk.get("page_number") or 0),
                asset_path=chunk.get("asset_path", ""),
                asset_mime_type=chunk.get("asset_mime_type", ""),
                embedding_modality=chunk.get("embedding_modality", "text"),
                content_hash=_hash_text(chunk["content"]),
                token_count=len(chunk["content"]),
                vector_status="pending",
                metadata_json={
                    "source": "postgresql_v2_ingestion",
                    "original_chunk_id": chunk["chunk_id"],
                },
            )
            for chunk in chunks
        ]

    async def _ensure_organization_exists(self, organization_id: str) -> None:
        organization_exists = getattr(self.documents, "organization_exists", None)
        if organization_exists and not await organization_exists(organization_id):
            raise ValueError(
                "organization_id does not exist. Use an existing organization id, "
                "for local testing: 00000000-0000-4000-8000-00000000a001"
            )


def _hash_text(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def _hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value or b"").hexdigest()


def _safe_file_name(value: str) -> str:
    name = Path(value or "unnamed").name
    return re.sub(r"[^0-9A-Za-z._\-\u4e00-\u9fff]+", "_", name) or "unnamed"


def _result(
    document: Document,
    *,
    duplicate: bool,
    chunk_count: int,
    version_id: str | None = None,
    file_id: str | None = None,
) -> dict[str, Any]:
    return {
        "document_id": document.id,
        "source_id": document.source_id,
        "title": document.title,
        "duplicate": duplicate,
        "chunk_count": chunk_count,
        "version_id": version_id,
        "file_id": file_id,
        "vector_status": "pending",
    }
