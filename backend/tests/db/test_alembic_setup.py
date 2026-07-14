from pathlib import Path
import os
import subprocess
import sys

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_has_five_ordered_stage_one_revisions():
    cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(cfg)
    revisions = list(script.walk_revisions(base="base", head="heads"))
    revision_ids = [revision.revision for revision in reversed(revisions)]

    assert revision_ids == [
        "001_organizations_projects",
        "002_resource_taxonomy",
        "003_documents_chunks",
        "004_resource_governance",
        "005_agent_runtime",
    ]


def test_alembic_env_exists():
    assert Path("alembic/env.py").exists()


def test_alembic_can_generate_postgresql_offline_sql():
    env = os.environ.copy()
    env["DATABASE_URL_SYNC"] = "postgresql+psycopg://wenchuang:wenchuang@localhost:5432/wenchuang"

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        check=False,
        capture_output=True,
        env=env,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "CREATE TABLE documents" in result.stdout
    assert "CREATE TABLE workflow_runs" in result.stdout
