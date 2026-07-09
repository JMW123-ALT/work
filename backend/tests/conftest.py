"""
pytest fixtures — 使用 FastAPI TestClient，所有测试共享一个应用实例
"""
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="shujuku-backend-test-"))
os.environ["DATA_DIR"] = str(TEST_DATA_DIR)
os.environ["UPLOAD_DIR"] = str(TEST_DATA_DIR / "uploads")
os.environ["CHROMA_PATH"] = str(TEST_DATA_DIR / "chroma")
os.environ["EMBEDDING_PROVIDER"] = "local"
os.environ["EMBEDDING_API_KEY"] = ""
os.environ["RERANK_PROVIDER"] = "passthrough"

from app.main import create_app


@pytest.fixture(scope="session")
def app():
    return create_app()


@pytest.fixture(scope="session")
def client(app):
    with TestClient(app) as c:
        yield c
