from app.services import rerank_client as rerank_module
from app.services.rerank_client import RerankClient, build_rerank_documents, rerank_url


def test_rerank_url_uses_configured_base_url():
    url = rerank_url("https://example.aliyuncs.com/api/v1")

    assert (
        url
        == "https://example.aliyuncs.com/api/v1/services/rerank/"
        "text-rerank/text-rerank"
    )


def test_rerank_url_accepts_full_endpoint():
    endpoint = (
        "https://example.aliyuncs.com/api/v1/services/rerank/"
        "text-rerank/text-rerank"
    )

    assert rerank_url(endpoint) == endpoint


def test_rerank_disabled_uses_passthrough(monkeypatch):
    monkeypatch.setattr(rerank_module.settings, "rerank_provider", "dashscope")
    monkeypatch.setattr(rerank_module.settings, "rerank_enabled", False, raising=False)
    monkeypatch.setattr(rerank_module.settings, "rerank_api_key", "token")

    def fail_if_called(self, query, chunks, top_n):
        raise AssertionError("rerank model should not be called when disabled")

    monkeypatch.setattr(RerankClient, "_rerank_dashscope", fail_if_called)

    result = RerankClient().rerank("query", [{"content": "doc", "score": 0.5}], top_n=1)

    assert result["mode"] == "passthrough"


def test_rerank_enabled_calls_dashscope(monkeypatch):
    monkeypatch.setattr(rerank_module.settings, "rerank_provider", "dashscope")
    monkeypatch.setattr(rerank_module.settings, "rerank_enabled", True, raising=False)
    monkeypatch.setattr(rerank_module.settings, "rerank_api_key", "token")

    called = {}

    def fake_rerank(self, query, chunks, top_n):
        called["query"] = query
        return {"items": chunks[:top_n], "mode": "dashscope", "model": self.model}

    monkeypatch.setattr(RerankClient, "_rerank_dashscope", fake_rerank)

    result = RerankClient().rerank("query", [{"content": "doc", "score": 0.5}], top_n=1)

    assert called["query"] == "query"
    assert result["mode"] == "dashscope"


def test_build_rerank_documents_uses_multimodal_shape_for_assets(tmp_path):
    image_path = tmp_path / "page.jpg"
    image_path.write_bytes(b"fake image bytes")

    docs = build_rerank_documents(
        [
            {
                "content": "PDF page text",
                "asset_path": str(image_path),
                "asset_mime_type": "image/jpeg",
            },
            {"content": "plain text only"},
        ],
        multimodal=True,
    )

    assert docs[0]["text"] == "PDF page text"
    assert docs[0]["image"].startswith("data:image/jpeg;base64,")
    assert docs[1] == {"text": "plain text only"}


def test_build_rerank_documents_keeps_string_shape_for_text_model(tmp_path):
    image_path = tmp_path / "page.jpg"
    image_path.write_bytes(b"fake image bytes")

    docs = build_rerank_documents(
        [{"content": "PDF page text", "asset_path": str(image_path)}],
        multimodal=False,
    )

    assert docs == ["PDF page text"]
