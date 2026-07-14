"""003 documents chunks

Revision ID: 003_documents_chunks
Revises: 002_resource_taxonomy
Create Date: 2026-07-14
"""

from alembic import op

from app.db.base import Base
import app.db.models  # noqa: F401

revision = "003_documents_chunks"
down_revision = "002_resource_taxonomy"
branch_labels = None
depends_on = None

TABLES = [
    "documents",
    "document_versions",
    "document_files",
    "chunks",
    "resource_category_links",
    "resource_tags",
]


def upgrade() -> None:
    bind = op.get_bind()
    for table_name in TABLES:
        Base.metadata.tables[table_name].create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in reversed(TABLES):
        Base.metadata.tables[table_name].drop(bind, checkfirst=True)
