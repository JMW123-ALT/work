def test_agent_chat_available_on_v1_prefix(client):
    resp = client.post(
        "/api/v1/chat",
        json={"query": "敦煌保温杯文创，偏国潮厚重风，输出小红书文案"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["user_query"] == "敦煌保温杯文创，偏国潮厚重风，输出小红书文案"
    assert data["intent"] == "copywriting"
    assert data["status"] in {"ok", "need_more_material", "need_human_review", "blocked"}
    assert "final_answer" in data


def test_agent_chat_available_on_compat_api_prefix(client):
    resp = client.post("/api/chat", json={"query": "敦煌保温杯文创"})

    assert resp.status_code == 200
    assert resp.json()["user_query"] == "敦煌保温杯文创"


def test_agent_chat_stream_available_on_v1_prefix(client):
    with client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={"query": "敦煌保温杯文创"},
    ) as resp:
        body = "".join(resp.iter_text())

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert "event: final" in body
    assert "data:" in body


def test_agent_chat_rejects_empty_query(client):
    resp = client.post("/api/v1/chat", json={"query": ""})

    assert resp.status_code == 422
