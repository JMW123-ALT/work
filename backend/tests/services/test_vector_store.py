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
