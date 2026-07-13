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

    assert resp.status_code == 422


def test_ingest_compat_accepts_frontend_file_upload(client):
    resp = client.post(
        "/api/ingest",
        data={
            "title": "上传 PDF 测试",
            "content": "前端备注",
            "object_type": "internal_doc",
            "permission_level": "public",
            "ingest_role": "admin",
            "operator": "pytest",
            "modality": "pdf",
        },
        files={
            "files": (
                "sample.pdf",
                b"%PDF-1.4\n% test pdf placeholder\n",
                "application/pdf",
            )
        },
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["item"]["title"] == "上传 PDF 测试"
    assert data["item"]["file_name"] == "sample.pdf"
    assert data["item"]["modality"] == "pdf"
