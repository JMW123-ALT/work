def test_platform_exposes_resource_categories(client):
    resp = client.get("/api/v1/resource-categories")

    assert resp.status_code == 200
    codes = {item["code"] for item in resp.json()["items"]}
    assert "internal.project.completed" in codes
    assert "other.cross_industry.story" in codes


def test_platform_exposes_agent_blueprints_without_executing_future_agents(client):
    resp = client.get("/api/v1/agent-runtime/blueprints")

    assert resp.status_code == 200
    by_code = {item["code"]: item for item in resp.json()["items"]}
    assert by_code["legacy_wenchuang_agent_v1"]["executable"] is True
    assert by_code["online_collection_agent"]["executable"] is False
    assert by_code["full_proposal_agent"]["phase"] == "future"


def test_platform_exposes_runtime_schema(client):
    resp = client.get("/api/v1/agent-runtime/schema")

    assert resp.status_code == 200
    data = resp.json()
    assert "waiting_user" in data["workflow_statuses"]
    assert "agent_evidence" in data["runtime_tables"]


def test_platform_exposes_database_health(client):
    resp = client.get("/api/v1/platform/database/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in {"not_configured", "ready", "unreachable", "no_migration"}
    assert isinstance(data["configured"], bool)
    assert isinstance(data["reachable"], bool)


def test_platform_text_ingestion_requires_configured_database(client):
    resp = client.post(
        "/api/v1/platform/resources/text",
        json={
            "organization_id": "org-1",
            "source_id": "src-1",
            "title": "测试资料",
            "content": "测试内容",
        },
    )

    assert resp.status_code == 503
    assert resp.json()["message"] == "DATABASE_URL is not configured"


def test_platform_file_ingestion_requires_configured_database(client):
    resp = client.post(
        "/api/v1/platform/resources/file",
        data={"organization_id": "org-1", "title": "测试文件"},
        files={"file": ("test.txt", b"hello", "text/plain")},
    )

    assert resp.status_code == 503
    assert resp.json()["message"] == "DATABASE_URL is not configured"


def test_platform_vector_index_requires_configured_database(client):
    resp = client.post("/api/v1/platform/vector-index/run", json={"limit": 10})

    assert resp.status_code == 503
    assert resp.json()["message"] == "DATABASE_URL is not configured"


def test_platform_v2_search_requires_configured_database(client):
    resp = client.post(
        "/api/v1/platform/search",
        json={"query": "秀洲区郊野公园方案", "top_k": 5, "min_confidence": 0.7},
    )

    assert resp.status_code == 503
    assert resp.json()["message"] == "DATABASE_URL is not configured"
