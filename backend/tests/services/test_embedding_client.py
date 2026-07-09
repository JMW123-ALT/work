from app.services.embedding_client import multimodal_embedding_url


def test_multimodal_embedding_url_uses_configured_base_url():
    url = multimodal_embedding_url("https://example.aliyuncs.com/api/v1")

    assert (
        url
        == "https://example.aliyuncs.com/api/v1/services/embeddings/"
        "multimodal-embedding/multimodal-embedding"
    )


def test_multimodal_embedding_url_accepts_full_endpoint():
    endpoint = (
        "https://example.aliyuncs.com/api/v1/services/embeddings/"
        "multimodal-embedding/multimodal-embedding"
    )

    assert multimodal_embedding_url(endpoint) == endpoint

