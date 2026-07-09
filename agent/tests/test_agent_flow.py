"""Agent 基础流程测试。

覆盖意图识别、前置风控和 Mock 检索这几个最小核心能力。
"""

import unittest

from wc_agent.agents import parse_intent_and_keywords
from wc_agent.guardrails import pre_guardrails_node
from wc_agent.retrievers import MockKnowledgeRetriever, ShujukuHttpRetriever, get_default_retriever
from wc_agent.settings import Settings
from wc_agent.state import AgentStatus, WenchuangState


class AgentFlowTests(unittest.TestCase):
    def test_intent_copywriting(self):
        intent, keywords, style = parse_intent_and_keywords("敦煌保温杯文创，输出小红书文案")
        self.assertEqual(intent, "copywriting")
        self.assertIn("敦煌保温杯文创", keywords)
        self.assertEqual(style, "国潮厚重风")

    def test_guardrails_blocks_cultural_risk(self):
        result = pre_guardrails_node(WenchuangState(user_query="帮我做一个篡改历史的恶搞文创"))
        self.assertEqual(result["status"], AgentStatus.BLOCKED)

    def test_mock_retriever_finds_dunhuang(self):
        evidence = MockKnowledgeRetriever().search("敦煌保温杯文创")
        self.assertTrue(evidence)
        self.assertGreaterEqual(evidence[0].confidence, 0.7)

    def test_default_retriever_can_use_shujuku_backend(self):
        retriever = get_default_retriever(Settings(retriever_provider="shujuku"))

        self.assertIsInstance(retriever, ShujukuHttpRetriever)


if __name__ == "__main__":
    unittest.main()
