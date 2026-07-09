def test_search_success(client):
    resp = client.post(
        "/api/v1/search",
        json={"query": "旅游景点", "user_type": "visitor"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "rerank" in data


def test_search_returns_agent_ready_evidence_items(client):
    resp = client.post(
        "/api/v1/search",
        json={
            "query": "旅游景点",
            "user_type": "visitor",
            "top_k": 3,
            "min_confidence": 0.0,
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["items"]

    item = data["items"][0]
    assert set(
        [
            "text",
            "source",
            "category",
            "culture_theme",
            "confidence",
            "copyright_status",
            "risk_level",
            "metadata",
        ]
    ).issubset(item.keys())
    assert item["text"]
    assert item["source"].startswith("shujuku:")
    assert 0 <= item["confidence"] <= 1
    assert "chunk_id" in item["metadata"]
    assert "source_id" in item["metadata"]


def test_search_filters_by_min_confidence(client):
    resp = client.post(
        "/api/v1/search",
        json={
            "query": "旅游景点",
            "user_type": "visitor",
            "top_k": 5,
            "min_confidence": 0.99,
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert all(item["confidence"] >= 0.99 for item in data["items"])


def test_search_empty_query(client):
    resp = client.post("/api/v1/search", json={"query": ""})
    assert resp.status_code == 422


def test_ask_success(client):
    resp = client.post(
        "/api/v1/ask",
        json={"question": "推荐几个适合家庭出游的景点"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "sources" in data
    assert "traceId" in data
