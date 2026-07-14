from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class Document(IdMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_id: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    object_type: Mapped[str] = mapped_column(String(80), nullable=False, default="internal_doc")
    access_channel: Mapped[str] = mapped_column(String(80), nullable=False, default="web")
    original_ref_uri: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    modality: Mapped[str] = mapped_column(String(40), nullable=False, default="text")
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")

    __table_args__ = (
        UniqueConstraint("organization_id", "source_id", name="uq_documents_org_source"),
        Index(
            "uq_documents_org_project_file_sha",
            "organization_id",
            "project_id",
            "file_sha256",
            unique=True,
            postgresql_where=file_sha256 != "",
        ),
    )


class DocumentVersion(IdMixin, TimestampMixin, Base):
    __tablename__ = "document_versions"

    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    parser: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    extraction_status: Mapped[str] = mapped_column(String(80), nullable=False, default="parsed")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "version",
            name="uq_document_versions_document_version",
        ),
    )


class DocumentFile(IdMixin, TimestampMixin, Base):
    __tablename__ = "document_files"

    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("document_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(300), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    file_size: Mapped[int] = mapped_column(nullable=False, default=0)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    file_role: Mapped[str] = mapped_column(String(50), nullable=False, default="original")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class Chunk(IdMixin, TimestampMixin, Base):
    __tablename__ = "chunks"

    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_version_id: Mapped[str] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    source_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    section_path: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    modality: Mapped[str] = mapped_column(String(40), nullable=False, default="text")
    parser: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    page_number: Mapped[int] = mapped_column(nullable=False, default=0)
    asset_path: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    asset_mime_type: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    embedding_modality: Mapped[str] = mapped_column(String(50), nullable=False, default="text")
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    token_count: Mapped[int] = mapped_column(nullable=False, default=0)
    embedding_model: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    embedding_version: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    vector_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "document_version_id",
            "chunk_index",
            name="uq_chunks_version_index",
        ),
    )
