"""演示案例回归测试。

确保 Swagger 中展示的 demo case 与真实 Agent 输出状态保持一致。
"""

import unittest
import os

os.environ["LLM_API_KEY"] = ""

from fastapi.testclient import TestClient

from wc_agent.api import DEMO_CASES, app
from wc_agent.graph import run_agent


class DemoCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_demo_cases_reach_expected_status(self):
        for demo_case in DEMO_CASES:
            with self.subTest(case_id=demo_case.id):
                result = await run_agent(demo_case.query)
                self.assertEqual(result.status.value, demo_case.expected_status)

    async def test_no_material_case_does_not_generate_plan(self):
        result = await run_agent("玛雅金字塔咖啡机周边方案")
        self.assertEqual(result.status.value, "need_more_material")
        self.assertFalse(result.design_plan)
        self.assertFalse(result.marketing_copy)

    async def test_copyright_case_marks_human_review(self):
        result = await run_agent("敦煌保温杯文创，想做故宫联名风格，输出电商卖点")
        self.assertEqual(result.status.value, "need_human_review")
        self.assertTrue(any("授权" in warning or "IP" in warning for warning in result.warnings))


class DemoCaseApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_get_single_demo_case(self):
        response = self.client.get("/demo-cases/dunhuang_cup")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["expected_status"], "ok")

    def test_run_all_demo_case_endpoints(self):
        for demo_case in DEMO_CASES:
            with self.subTest(case_id=demo_case.id):
                response = self.client.post(f"/demo-cases/{demo_case.id}/run")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], demo_case.expected_status)


if __name__ == "__main__":
    unittest.main()
