"""AgentRouter 扩展口。

本次重构不接入任何生产路由，所有方法明确抛出 NotImplementedError。
未来在此实现意图分类 → Agent 选择 → Agent 运行的统一入口。

注意：此文件不在 api/v1/router.py 中注册任何 HTTP 路由。
"""

from __future__ import annotations


class AgentRouter:
    """统一 Agent 路由入口（未实现）。

    未来实现步骤：
    1. classify_intent：通过 LLM 或规则识别用户意图
    2. resolve_agent：根据意图代码查找对应 Agent 类
    3. run_agent：实例化 Agent 并执行 run()
    """

    async def classify_intent(self, query: str, context: dict) -> str:
        """识别用户意图，返回 intent 代码。"""
        raise NotImplementedError("AgentRouter.classify_intent is not yet implemented.")

    async def resolve_agent(self, intent: str):
        """根据意图代码返回对应 Agent 类。"""
        raise NotImplementedError("AgentRouter.resolve_agent is not yet implemented.")

    async def run_agent(self, agent_code: str, request: dict) -> dict:
        """按 agent_code 路由并运行对应 Agent。"""
        raise NotImplementedError("AgentRouter.run_agent is not yet implemented.")
