from sqlalchemy import ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class ResourcePermission(IdMixin, TimestampMixin, Base):
    __tablename__ = "resource_permissions"

    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope_type: Mapped[str] = mapped_column(String(40), nullable=False)
    scope_id: Mapped[str] = mapped_column(String(120), nullable=False)
    access_level: Mapped[str] = mapped_column(String(40), nullable=False, default="read")

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "scope_type",
            "scope_id",
            "access_level",
            name="uq_resource_permission_scope",
        ),
    )


class DocumentGovernance(IdMixin, TimestampMixin, Base):
    __tablename__ = "document_governance"

    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    confidentiality_level: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="public",
    )
    copyright_status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="unknown",
    )
    risk_level: Mapped[str] = mapped_column(String(40), nullable=False, default="low")
    lifecycle_status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="draft",
    )


class IngestionTask(IdMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_tasks"

    document_id: Mapped[str | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task_type: Mapped[str] = mapped_column(String(80), nullable=False, default="upload")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class VectorIndexTask(IdMixin, TimestampMixin, Base):
    __tablename__ = "vector_index_tasks"

    document_id: Mapped[str | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    collection_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    embedding_model: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    chunk_count: Mapped[int] = mapped_column(nullable=False, default=0)
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")


class OnlineCollectionTask(IdMixin, TimestampMixin, Base):
    __tablename__ = "online_collection_tasks"

    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    query_plan_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    result_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
