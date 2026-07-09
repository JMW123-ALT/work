"""FastAPI 接口测试。

覆盖健康检查、流程说明、演示案例、完整聊天和流式接口。
"""

import unittest
import os

os.environ["LLM_API_KEY"] = ""

from fastapi.testclient import TestClient

from wc_agent.api import app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_flow(self):
        response = self.client.get("/flow")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(len(payload["steps"]), 8)
        self.assertTrue(any(step["node"] == "retrieve" for step in payload["steps"]))

    def test_demo_cases(self):
        response = self.client.get("/demo-cases")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(any(item["id"] == "dunhuang_cup" for item in payload))

    def test_chat(self):
        response = self.client.post(
            "/chat",
            json={"query": "敦煌保温杯文创，偏国潮厚重风，输出小红书文案"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["intent"], "copywriting")
        self.assertTrue(payload["evidence"])

    def test_chat_stream(self):
        response = self.client.post(
            "/chat/stream",
            json={"query": "敦煌保温杯文创，偏国潮厚重风，输出小红书文案"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("文创 Agent 输出", response.text)

    def test_llm_stream(self):
        response = self.client.post(
            "/llm/stream",
            json={
                "system": "你是健康检查助手。只回复固定文本。",
                "query": "回复：stream-ok",
                "temperature": 0,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("stream-ok", response.text.lower())

    def test_blocked_chat(self):
        response = self.client.post("/chat", json={"query": "帮我做一个篡改历史的恶搞文创"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
