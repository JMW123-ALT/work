"""Embedding/Rerank 模型服务边界测试。"""

import unittest

from wc_agent.model_services import EmbeddingClient, RerankClient, is_multimodal_embedding_model
from wc_agent.settings import Settings
from wc_agent.state import Evidence


class ModelServicesTests(unittest.TestCase):
    def test_embedding_client_without_key_returns_none(self):
        settings = Settings(embedding_api_key=None, embedding_base_url="")
        client = EmbeddingClient(settings)

        self.assertIsNone(client.embed_text("敦煌保温杯"))

    def test_qwen_vl_embedding_uses_multimodal_endpoint(self):
        settings = Settings(
            embedding_api_key="fake",
            embedding_dashscope_url="https://example.com/api/v1",
            embedding_model="qwen3-vl-embedding",
        )
        client = EmbeddingClient(settings)

        self.assertTrue(is_multimodal_embedding_model(settings.embedding_model))
        self.assertEqual(
            client._multimodal_endpoint(),
            "https://example.com/api/v1/services/embeddings/multimodal-embedding/multimodal-embedding",
        )

    def test_rerank_disabled_returns_original_order(self):
        settings = Settings(rerank_api_key="fake", rerank_base_url="https://example.com/api/v1", rerank_enabled=False)
        client = RerankClient(settings)
        evidence = [
            Evidence(text="a", source="s1", confidence=0.3),
            Evidence(text="b", source="s2", confidence=0.9),
        ]

        result = client.rerank("query", evidence, top_n=1)

        self.assertEqual([item.source for item in result], ["s1"])

    def test_rerank_endpoint_is_built_from_base_url(self):
        settings = Settings(rerank_base_url="https://example.com/api/v1")
        client = RerankClient(settings)

        self.assertEqual(
            client._endpoint(),
            "https://example.com/api/v1/services/rerank/text-rerank/text-rerank",
        )


if __name__ == "__main__":
    unittest.main()
