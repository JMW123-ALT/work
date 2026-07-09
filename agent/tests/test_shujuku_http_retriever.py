"""同仓库 backend 检索接口适配器测试。"""

import unittest

import httpx

from wc_agent.retrievers import ShujukuHttpRetriever
from wc_agent.settings import Settings


class ShujukuHttpRetrieverTests(unittest.TestCase):
    def test_search_converts_backend_items_to_evidence(self):
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/api/v1/search")
            payload = request.read().decode("utf-8")
            self.assertIn("敦煌保温杯", payload)
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "text": "敦煌藻井纹样适合提取为杯身装饰元素。",
                            "source": "shujuku:source-001",
                            "category": "culture_doc",
                            "culture_theme": "敦煌藻井",
                            "confidence": 0.86,
                            "copyright_status": "public_domain",
                            "risk_level": "low",
                            "metadata": {"chunk_id": "chunk-001"},
                        }
                    ],
                    "blockedCount": 0,
                    "permissionNotice": "",
                    "rerank": {"mode": "passthrough", "model": "passthrough"},
                },
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        retriever = ShujukuHttpRetriever(
            settings=Settings(
                shujuku_search_url="http://backend.test/api/v1/search",
                min_confidence=0.7,
            ),
            http_client=client,
        )

        evidence = retriever.search("敦煌保温杯", n_results=3)

        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].text, "敦煌藻井纹样适合提取为杯身装饰元素。")
        self.assertEqual(evidence[0].source, "shujuku:source-001")
        self.assertEqual(evidence[0].category, "culture_doc")
        self.assertEqual(evidence[0].culture_theme, "敦煌藻井")
        self.assertEqual(evidence[0].confidence, 0.86)

    def test_search_returns_empty_list_when_backend_is_unavailable(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("backend down", request=request)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        retriever = ShujukuHttpRetriever(
            settings=Settings(shujuku_search_url="http://backend.test/api/v1/search"),
            http_client=client,
        )

        self.assertEqual(retriever.search("敦煌保温杯"), [])


if __name__ == "__main__":
    unittest.main()
