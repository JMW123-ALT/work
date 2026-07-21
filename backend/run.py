"""Backend startup entry.

Usage:
  python run.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
VENV_PYTHON = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"

if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    os.execv(
        str(VENV_PYTHON),
        [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]],
    )

# Ensure backend/ is first on sys.path so `from app.xxx` resolves correctly.
sys.path.insert(0, str(BACKEND_DIR))

import uvicorn

from app.core.config import settings


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "local",
        log_level=settings.log_level.lower(),
    )
