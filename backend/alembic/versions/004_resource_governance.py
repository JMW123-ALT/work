"""004 resource governance

Revision ID: 004_resource_governance
Revises: 003_documents_chunks
Create Date: 2026-07-14
"""

from alembic import op

from app.db.base import Base
import app.db.models  # noqa: F401

revision = "004_resource_governance"
down_revision = "003_documents_chunks"
branch_labels = None
depends_on = None

TABLES = [
    "resource_permissions",
    "document_governance",
    "ingestion_tasks",
    "vector_index_tasks",
    "online_collection_tasks",
]


def upgrade() -> None:
    bind = op.get_bind()
    for table_name in TABLES:
        Base.metadata.tables[table_name].create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in reversed(TABLES):
        Base.metadata.tables[table_name].drop(bind, checkfirst=True)
