"""005 agent runtime

Revision ID: 005_agent_runtime
Revises: 004_resource_governance
Create Date: 2026-07-14
"""

from alembic import op

from app.db.base import Base
import app.db.models  # noqa: F401

revision = "005_agent_runtime"
down_revision = "004_resource_governance"
branch_labels = None
depends_on = None

TABLES = [
    "workflow_runs",
    "agent_runs",
    "agent_run_steps",
    "artifacts",
    "artifact_versions",
    "artifact_dependencies",
    "agent_evidence",
    "reviews",
    "prompt_templates",
    "platform_profiles",
    "intelligence_items",
]


def upgrade() -> None:
    bind = op.get_bind()
    for table_name in TABLES:
        Base.metadata.tables[table_name].create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in reversed(TABLES):
        Base.metadata.tables[table_name].drop(bind, checkfirst=True)
