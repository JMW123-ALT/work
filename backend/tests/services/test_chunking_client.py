from app.services.chunking_client import ChunkingClient


def test_image_document_keeps_original_file_as_multimodal_asset(tmp_path):
    image_path = tmp_path / "poster.png"
    image_path.write_bytes(b"fake image bytes")
    client = ChunkingClient()

    chunks = client.chunk_document(
        source_id="src-image-asset-test",
        title="poster",
        content="jiangnan water-town poster",
        modality="image",
        section_path="poster",
        file_path=str(image_path),
        mime_type="image/png",
    )

    assert len(chunks) == 1
    assert chunks[0]["asset_path"] == str(image_path)
    assert chunks[0]["asset_mime_type"] == "image/png"
    assert chunks[0]["embedding_modality"] == "image"


def test_pdf_chunks_keep_page_boundaries_from_page_markers():
    client = ChunkingClient()
    content = (
        "【第 1 页】\n"
        "第一页独有内容，包含入口服务、湿地栈道和游客中心。\n\n"
        "【第 2 页】\n"
        "第二页独有内容，包含亲子课堂、田园市集和夜游活动。"
    )

    chunks = client.chunk_document(
        source_id="src-pdf-page-test",
        title="PDF 分页测试",
        content=content,
        modality="pdf",
        section_path="PDF 分页测试",
    )

    assert len(chunks) == 2
    assert chunks[0]["section_path"].endswith("第 1 页")
    assert chunks[1]["section_path"].endswith("第 2 页")
    assert "第二页独有内容" not in chunks[0]["content"]
    assert "第一页独有内容" not in chunks[1]["content"]
