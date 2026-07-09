def test_ingest_text_success(client):
    resp = client.post(
        "/api/v1/ingest/text",
        json={
            "title": "FastAPI 测试文档",
            "content": "这是一段用于测试的内容，验证入库流程是否正常。",
            "ingest_role": "admin",
            "operator": "pytest",
            "permission_level": "public",
        },
    )
    assert resp.status_code == 201
    item = resp.json()["item"]
    assert item["title"] == "FastAPI 测试文档"
    assert item["chunk_count"] >= 1


def test_ingest_text_forbidden(client):
    resp = client.post(
        "/api/v1/ingest/text",
        json={
            "title": "受限文档",
            "content": "内容",
            "ingest_role": "none",
        },
    )
    assert resp.status_code == 403


def test_ingest_text_missing_content(client):
    resp = client.post(
        "/api/v1/ingest/text",
        json={"title": "只有标题"},
    )
    assert resp.status_code == 422  # Pydantic 校验失败
