from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class ResourceCategory(IdMixin, TimestampMixin, Base):
    __tablename__ = "resource_categories"

    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("resource_categories.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ResourceCategoryLink(IdMixin, TimestampMixin, Base):
    __tablename__ = "resource_category_links"

    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[str] = mapped_column(
        ForeignKey("resource_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "category_id",
            name="uq_resource_category_link_document_category",
        ),
        Index(
            "uq_resource_category_link_one_primary",
            "document_id",
            unique=True,
            postgresql_where=is_primary.is_(True),
        ),
    )


class Tag(IdMixin, TimestampMixin, Base):
    __tablename__ = "tags"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(100), nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "normalized_name", name="uq_tags_org_name"),
    )


class ResourceTag(IdMixin, TimestampMixin, Base):
    __tablename__ = "resource_tags"

    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tag_id: Mapped[str] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint("document_id", "tag_id", name="uq_resource_tags_document_tag"),
    )
