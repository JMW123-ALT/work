def test_openapi_shows_agent_but_hides_frontend_internal_routes(client):
    resp = client.get("/api/openapi.json")

    assert resp.status_code == 200
    paths = resp.json()["paths"]

    assert "/api/v1/chat" in paths
    assert "/api/v1/health" in paths
    assert "/api/v1/documents" not in paths
    assert "/api/v1/ingest/text" not in paths
    assert "/api/v1/ingest/file" not in paths
    assert "/api/v1/search" not in paths
    assert "/api/v1/ask" not in paths


def test_hidden_internal_routes_are_still_callable(client):
    ingest_resp = client.post(
        "/api/v1/ingest/text",
        json={
            "title": "隐藏文档测试",
            "content": "接口从 Swagger 隐藏，但仍然可以被前端或程序调用。",
            "ingest_role": "admin",
            "operator": "pytest",
            "permission_level": "public",
        },
    )
    assert ingest_resp.status_code == 201

    search_resp = client.post(
        "/api/v1/search",
        json={"query": "隐藏文档测试", "min_confidence": 0},
    )
    assert search_resp.status_code == 200
