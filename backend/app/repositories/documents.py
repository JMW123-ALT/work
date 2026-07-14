from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.documents import Chunk, Document, DocumentFile, DocumentVersion
from app.db.models.organization import Organization
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    model = Document

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_source_id(
        self,
        organization_id: str,
        source_id: str,
    ) -> Document | None:
        result = await self.session.execute(
            select(Document).where(
                Document.organization_id == organization_id,
                Document.source_id == source_id,
            )
        )
        return result.scalar_one_or_none()

    async def organization_exists(self, organization_id: str) -> bool:
        result = await self.session.execute(
            select(Organization.id).where(Organization.id == organization_id)
        )
        return result.scalar_one_or_none() is not None

    async def get_by_file_sha256(
        self,
        organization_id: str,
        project_id: str | None,
        file_sha256: str,
    ) -> Document | None:
        if not file_sha256:
            return None
        result = await self.session.execute(
            select(Document).where(
                Document.organization_id == organization_id,
                Document.project_id == project_id,
                Document.file_sha256 == file_sha256,
                Document.status != "deleted",
            )
        )
        return result.scalar_one_or_none()

    async def add_version(self, version: DocumentVersion) -> DocumentVersion:
        self.session.add(version)
        await self.session.flush()
        return version

    async def add_file(self, file: DocumentFile) -> DocumentFile:
        self.session.add(file)
        await self.session.flush()
        return file

    async def replace_chunks(
        self,
        document_version_id: str,
        chunks: list[Chunk],
    ) -> list[Chunk]:
        existing = await self.session.execute(
            select(Chunk).where(Chunk.document_version_id == document_version_id)
        )
        for item in existing.scalars().all():
            await self.session.delete(item)
        for chunk in chunks:
            self.session.add(chunk)
        await self.session.flush()
        return chunks
