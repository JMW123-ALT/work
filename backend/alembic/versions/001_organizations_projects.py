"""001 organizations projects

Revision ID: 001_organizations_projects
Revises:
Create Date: 2026-07-14
"""

from alembic import op

from app.db.base import Base
import app.db.models  # noqa: F401

revision = "001_organizations_projects"
down_revision = None
branch_labels = None
depends_on = None

TABLES = [
    "organizations",
    "users",
    "projects",
    "project_members",
    "project_requirements",
]


def upgrade() -> None:
    bind = op.get_bind()
    for table_name in TABLES:
        Base.metadata.tables[table_name].create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in reversed(TABLES):
        Base.metadata.tables[table_name].drop(bind, checkfirst=True)
