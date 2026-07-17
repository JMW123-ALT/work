"""006 permission status seed

Add permission_level + error_message to documents (idempotent via IF NOT EXISTS),
add check constraints using short names (naming convention → ck_documents_<name>),
and seed the default organization for single-org local mode.

Revision ID: 006_permission_status_seed
Revises: 005_agent_runtime
Create Date: 2026-07-16
"""

from alembic import context, op
from sqlalchemy import inspect as sa_inspect, text

revision = "006_permission_status_seed"
down_revision = "005_agent_runtime"
branch_labels = None
depends_on = None

DEFAULT_ORG_ID = "00000000-0000-4000-8000-00000000a001"


def _full_constraint_name(table: str, short_name: str, kind: str = "ck") -> str:
    """Reconstruct the name produced by NAMING_CONVENTION.

    ck: "ck_%(table_name)s_%(constraint_name)s"
    """
    if kind == "ck":
        return f"ck_{table}_{short_name}"
    raise ValueError(f"Unknown kind: {kind}")


def _constraint_exists(bind, table: str, full_name: str) -> bool:
    inspector = sa_inspect(bind)
    existing = {c["name"] for c in inspector.get_check_constraints(table)}
    return full_name in existing


def _index_exists(bind, table: str, index_name: str) -> bool:
    inspector = sa_inspect(bind)
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()

    # ── 1. Add permission_level column IF NOT EXISTS ───────────────────────
    bind.execute(text(
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS "
        "permission_level VARCHAR(30) NOT NULL DEFAULT 'internal'"
    ))

    # ── 2. Add error_message column IF NOT EXISTS ─────────────────────────
    bind.execute(text(
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS "
        "error_message VARCHAR(2000) NOT NULL DEFAULT ''"
    ))

    # ── 3. permission_level check constraint ──────────────────────────────
    full_perm = _full_constraint_name("documents", "permission_level")
    if not _constraint_exists(bind, "documents", full_perm):
        # Use short name so Alembic naming-convention expands to full_perm
        op.create_check_constraint(
            "permission_level",
            "documents",
            "permission_level IN ('public','free','paid','internal','restricted')",
        )

    # ── 4. Migrate any stale 'active' rows → 'ready' ─────────────────────
    if not context.is_offline_mode():
        bind.execute(
            text("UPDATE documents SET status = 'ready' WHERE status = 'active'")
        )

    # ── 5. status check constraint ────────────────────────────────────────
    full_status = _full_constraint_name("documents", "status")
    if not _constraint_exists(bind, "documents", full_status):
        op.create_check_constraint(
            "status",
            "documents",
            "status IN ('queued','parsing','embedding','ready','failed','deleting','deleted')",
        )

    # ── 6. Indexes ────────────────────────────────────────────────────────
    if not _index_exists(bind, "documents", "ix_documents_permission_level"):
        op.create_index("ix_documents_permission_level", "documents", ["permission_level"])
    if not _index_exists(bind, "documents", "ix_documents_status"):
        op.create_index("ix_documents_status", "documents", ["status"])

    # ── 7. Seed default organization ──────────────────────────────────────
    if not context.is_offline_mode():
        row = bind.execute(
            text("SELECT id FROM organizations WHERE id = :id"),
            {"id": DEFAULT_ORG_ID},
        ).fetchone()
        if row is None:
            bind.execute(
                text(
                    "INSERT INTO organizations (id, name, code, status, created_at, updated_at) "
                    "VALUES (:id, :name, :code, :status, NOW(), NOW())"
                ),
                {
                    "id": DEFAULT_ORG_ID,
                    "name": "默认组织",
                    "code": "default",
                    "status": "active",
                },
            )


def downgrade() -> None:
    bind = op.get_bind()

    for idx in ("ix_documents_status", "ix_documents_permission_level"):
        if _index_exists(bind, "documents", idx):
            op.drop_index(idx, table_name="documents")

    for short_name in ("status", "permission_level"):
        full = _full_constraint_name("documents", short_name)
        if _constraint_exists(bind, "documents", full):
            op.drop_constraint(full, "documents", type_="check")

    inspector = sa_inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns("documents")}
    for col in ("permission_level", "error_message"):
        if col in existing_cols:
            op.drop_column("documents", col)
