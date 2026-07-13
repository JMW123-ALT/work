from app.services import vector_store as vector_store_module
from app.services.vector_store import vector_store


def test_similarity_search_with_relevance_scores_returns_document_score_pairs():
    vector_store.upsert_document(
        {
            "source_id": "src-vector-score-test",
            "title": "旅游景点测试资料",
            "content": "适合家庭出游的旅游景点包含亲子活动、自然游线和休闲服务。",
            "object_type": "internal_doc",
            "permission_level": "public",
            "access_channel": "web",
            "original_ref_uri": "manual://pytest",
            "section_path": "旅游景点测试资料",
            "modality": "text",
        },
        runtime=True,
    )

    pairs = vector_store.similarity_search_with_relevance_scores(
        "旅游景点",
        user_type="visitor",
        k=3,
    )

    assert pairs
    document, score = pairs[0]
    assert isinstance(document, dict)
    assert document["page_content"]
    assert "metadata" in document
    assert 0 <= score <= 1


def test_search_deduplicates_identical_chunk_content():
    content = "重复检索测试资料，包含湿地栈道、田园市集、亲子课堂和入口服务。"
    for source_id in ("src-duplicate-search-a", "src-duplicate-search-b"):
        vector_store.upsert_document(
            {
                "source_id": source_id,
                "title": "重复检索测试",
                "content": content,
                "object_type": "internal_doc",
                "permission_level": "public",
                "access_channel": "web",
                "original_ref_uri": f"manual://{source_id}",
                "section_path": "重复检索测试",
                "modality": "text",
            },
            runtime=True,
        )

    result = vector_store.search("湿地栈道 田园市集", user_type="visitor", top_k=10)
    matching = [item for item in result["items"] if item["content"] == content]

    assert len(matching) == 1


def test_image_document_uses_multimodal_embedding(monkeypatch, tmp_path):
    image_path = tmp_path / "poster.png"
    image_path.write_bytes(b"fake image bytes")
    called = {}

    def fake_embed_multimodal(text, *, image_path="", image_url="", mime_type=""):
        called["image_path"] = image_path
        called["mime_type"] = mime_type
        return {"type": "dense", "data": [1.0] + [0.0] * 1023}

    monkeypatch.setattr(
        vector_store_module.embedding_client,
        "embed_multimodal",
        fake_embed_multimodal,
    )

    vector_store.upsert_document(
        {
            "source_id": "src-image-multimodal-vector-test",
            "title": "image multimodal vector test",
            "content": "poster image with cultural symbols",
            "object_type": "internal_doc",
            "permission_level": "public",
            "access_channel": "web",
            "original_ref_uri": "manual://pytest-image",
            "section_path": "image multimodal vector test",
            "modality": "image",
            "file_path": str(image_path),
            "mime_type": "image/png",
        },
        runtime=True,
    )

    assert called["image_path"] == str(image_path)
    assert called["mime_type"] == "image/png"
