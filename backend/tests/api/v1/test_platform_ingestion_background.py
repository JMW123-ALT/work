import io

import pytest
from fastapi import BackgroundTasks, UploadFile

from app.api.v1 import platform
from app.schemas.platform import PlatformTextIngestRequest


class FakeSession:
    def __init__(self, events):
        self.events = events

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def commit(self):
        self.events.append("commit")


class FakeIngestionService:
    def __init__(self, session, *, events):
        self.events = events

    async def create_text_document(self, **kwargs):
        self.events.append("create_text")
        return _result(kwargs["source_id"], kwargs["title"])

    async def create_file_document(self, **kwargs):
        self.events.append("create_file")
        return _result(kwargs["source_id"] or "src-file", kwargs["title"] or "sample")


def _result(source_id, title):
    return {
        "document_id": "doc-1",
        "source_id": source_id,
        "title": title,
        "duplicate": False,
        "chunk_count": 1,
        "version_id": "version-1",
        "file_id": None,
        "vector_status": "pending",
    }


def _patch_ingestion(monkeypatch, events):
    session = FakeSession(events)
    monkeypatch.setattr(platform, "async_session_factory", lambda: session)
    monkeypatch.setattr(
        platform,
        "DocumentIngestionService",
        lambda current_session: FakeIngestionService(current_session, events=events),
    )


@pytest.mark.asyncio
async def test_text_ingestion_commits_before_scheduling_vector_index(monkeypatch):
    events = []
    _patch_ingestion(monkeypatch, events)
    background_tasks = BackgroundTasks()

    result = await platform.ingest_text_resource(
        PlatformTextIngestRequest(
            organization_id="org-1",
            source_id="src-text",
            title="正文测试",
            content="正文内容",
        ),
        background_tasks,
    )

    assert events == ["create_text", "commit"]
    assert result["vector_status"] == "pending"
    assert len(background_tasks.tasks) == 1
    assert background_tasks.tasks[0].func is platform._index_pending_in_background


@pytest.mark.asyncio
async def test_file_ingestion_commits_before_scheduling_vector_index(monkeypatch):
    events = []
    _patch_ingestion(monkeypatch, events)
    background_tasks = BackgroundTasks()
    upload = UploadFile(filename="sample.txt", file=io.BytesIO("文件正文".encode("utf-8")))

    result = await platform.ingest_file_resource(
        file=upload,
        organization_id="org-1",
        title="文件测试",
        source_id="src-file",
        background_tasks=background_tasks,
    )

    assert events == ["create_file", "commit"]
    assert result["vector_status"] == "pending"
    assert len(background_tasks.tasks) == 1
    assert background_tasks.tasks[0].func is platform._index_pending_in_background
