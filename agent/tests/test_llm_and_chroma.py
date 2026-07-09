"""LLM 与 Chroma 边界测试。"""

import tempfile
import unittest
from pathlib import Path

import openai

from wc_agent.llm import UnifiedLLM
from wc_agent.retrievers import ChromaRetriever, chroma_result_to_evidence
from wc_agent.settings import Settings


class LlmAndChromaTests(unittest.IsolatedAsyncioTestCase):
    async def test_openai_package_is_installed(self):
        self.assertTrue(openai.__version__)

    async def test_mock_stream_chat_yields_chunks(self):
        llm = UnifiedLLM(Settings(llm_api_key=None))
        chunks = [chunk async for chunk in llm.stream_chat("文化考据 Agent", "敦煌保温杯")]
        self.assertTrue(chunks)
        self.assertIn("文化溯源", "".join(chunks))

    async def test_empty_chroma_retriever_returns_empty_list(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            retriever = ChromaRetriever(path=Path(tmpdir), collection_name="test_collection")
            self.assertEqual(retriever.search("敦煌保温杯"), [])

    async def test_chroma_metadata_maps_to_evidence(self):
        metadata = {
            "chunk_id": "chunk-001",
            "source_id": "source-001",
            "chunk_index": 0,
            "section_path": "敦煌/藻井",
            "modality": "text",
            "parser": "markdown",
            "title": "敦煌藻井资料",
            "object_type": "culture_doc",
            "permission_level": "public",
            "access_channel": "web",
            "original_ref_uri": "seed://dunhuang",
            "file_name": "dunhuang.md",
            "mime_type": "text/markdown",
            "file_size": 100,
            "chunk_count": 3,
            "extraction_status": "parsed",
            "runtime": 0,
            "created_at": "2026-07-09T00:00:00Z",
            "updated_at": "2026-07-09T00:00:00Z",
        }
        evidence = chroma_result_to_evidence("chunk 正文内容", metadata, 0.82)

        self.assertEqual(evidence.text, "chunk 正文内容")
        self.assertEqual(evidence.source, "shujuku:source-001")
        self.assertEqual(evidence.category, "culture_doc")
        self.assertEqual(evidence.culture_theme, "敦煌藻井资料")
        self.assertEqual(evidence.copyright_status, "public_domain")
        self.assertEqual(evidence.risk_level, "low")
        self.assertEqual(evidence.confidence, 0.82)


if __name__ == "__main__":
    unittest.main()
