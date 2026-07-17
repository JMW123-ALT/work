import subprocess
import sys
from pathlib import Path


def test_rebuild_chroma_help_describes_postgresql_v2_command():
    backend_dir = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/rebuild_chroma.py", "--help"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "PostgreSQL" in result.stdout
    assert "Chroma v2" in result.stdout
