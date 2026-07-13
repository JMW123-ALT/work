from app.services.embedding_client import multimodal_content_items, multimodal_embedding_url


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


def test_multimodal_embedding_url_prefers_native_base_for_vl_model():
    url = multimodal_embedding_url(
        "https://example.aliyuncs.com/compatible-mode/v1",
        native_base_url="https://example.aliyuncs.com/api/v1",
    )

    assert (
        url
        == "https://example.aliyuncs.com/api/v1/services/embeddings/"
        "multimodal-embedding/multimodal-embedding"
    )


def test_multimodal_content_items_include_text_and_image_data_url(tmp_path):
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"fake image bytes")

    contents = multimodal_content_items(
        text="图片里的文创符号",
        image_path=str(image_path),
        mime_type="image/png",
    )

    assert contents[0] == {"text": "图片里的文创符号"}
    assert contents[1]["image"].startswith("data:image/png;base64,")

