"""FastAPI 对外接口。

这里提供给前端、Swagger 或其他服务调用的 HTTP API。
核心业务仍然委托给 `graph.run_agent()`，API 层只做请求/响应包装。
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .graph import run_agent
from .llm import UnifiedLLM
from .state import WenchuangState


class ChatRequest(BaseModel):
    """完整 Agent 调用请求。"""

    query: str = Field(..., min_length=1, description="用户文创需求")


class LlmStreamRequest(BaseModel):
    """直接测试 LLM Streaming 的请求。"""

    query: str = Field(..., min_length=1, description="要发送给 LLM 的用户问题")
    system: str = Field("你是文创 Agent 助手，请用中文给出简洁、可执行的回答。", description="系统提示词")
    temperature: float = Field(0.3, ge=0, le=2, description="生成温度")


class FlowStep(BaseModel):
    """工作流节点说明，用于 `/flow` 接口展示。"""

    node: str
    name: str
    description: str


class FlowBranch(BaseModel):
    """工作流分支说明，用于展示异常路径。"""

    from_node: str
    condition: str
    to_node: str


class DemoCase(BaseModel):
    """Swagger 中可直接运行的演示案例。"""

    id: str
    title: str
    query: str
    expected_status: str
    capability: str
    expected: str


FLOW_STEPS = [
    FlowStep(node="intent", name="需求解析", description="识别任务类型、关键词和风格变量。"),
    FlowStep(node="pre_guardrails", name="前置风控", description="拦截篡改历史、低俗化、历史虚无主义等高风险输入。"),
    FlowStep(node="retrieve", name="检索适配层", description="当前使用本地 Mock 知识库，后续替换为同事数据库适配器。"),
    FlowStep(node="post_guardrails", name="后置风控", description="根据证据版权状态和风险等级标记人工复核。"),
    FlowStep(node="cultural_review", name="文化考据", description="输出文化溯源、可用元素、慎用点、史料来源和人工核验点。"),
    FlowStep(node="design", name="创意设计", description="输出产品定位、设计思路、款式、视觉元素和工艺建议。"),
    FlowStep(node="marketing", name="营销优化", description="输出小红书、抖音、电商详情页卖点和推荐标签。"),
    FlowStep(node="final", name="最终输出", description="汇总任务识别、风险提示、检索证据、方案和文案。"),
]

FLOW_BRANCHES = [
    FlowBranch(from_node="pre_guardrails", condition="命中文化安全高风险", to_node="final"),
    FlowBranch(from_node="pre_guardrails", condition="通过前置风控", to_node="retrieve"),
    FlowBranch(from_node="retrieve", condition="无高置信度史料", to_node="cultural_review"),
    FlowBranch(from_node="retrieve", condition="检索到可用史料", to_node="post_guardrails"),
    FlowBranch(from_node="cultural_review", condition="资料不足或已拦截", to_node="final"),
    FlowBranch(from_node="cultural_review", condition="可继续生成", to_node="design"),
]

DEMO_CASES = [
    DemoCase(
        id="dunhuang_cup",
        title="敦煌保温杯文创",
        query="敦煌保温杯文创，偏国潮厚重风，输出小红书文案",
        expected_status="ok",
        capability="完整生成链路",
        expected="检索敦煌藻井、壁画色彩和保温杯产品结构，生成文化考据、产品方案和营销文案。",
    ),
    DemoCase(
        id="intangible_pattern",
        title="非遗纹样文案",
        query="非遗纹样文创，帮我生成小红书种草文案",
        expected_status="ok",
        capability="非遗合规表达",
        expected="强调非遗授权与工艺关系，输出适合小红书的合规表达。",
    ),
    DemoCase(
        id="exhibition_plan",
        title="博物馆策展方案",
        query="帮我做一个唐代纹样主题的博物馆策展方案",
        expected_status="ok",
        capability="策展方案识别",
        expected="识别为策展任务，输出主题立意、展区结构和互动传播方向。",
    ),
    DemoCase(
        id="copyright_review",
        title="商用 IP 版权复核",
        query="敦煌保温杯文创，想做故宫联名风格，输出电商卖点",
        expected_status="need_human_review",
        capability="版权风险标记",
        expected="识别疑似商用 IP/联名授权风险，继续生成草案但标注人工复核。",
    ),
    DemoCase(
        id="no_material",
        title="无史料补充提示",
        query="玛雅金字塔咖啡机周边方案",
        expected_status="need_more_material",
        capability="无资料分支",
        expected="Mock 知识库无匹配史料时，不强行生成方案，提示补充素材或等待数据库。",
    ),
    DemoCase(
        id="blocked_risk",
        title="风险拦截样例",
        query="帮我做一个篡改历史的恶搞文创",
        expected_status="blocked",
        capability="文化安全拦截",
        expected="命中文化安全风险，直接 blocked，不进入生成链路。",
    ),
]


def create_app():
    """创建 FastAPI 应用。

    把创建过程放进函数里，便于测试中直接导入 `app`。
    """

    try:
        from fastapi import FastAPI
    except ImportError as exc:
        raise RuntimeError("FastAPI is not installed. Run: pip install fastapi") from exc

    app = FastAPI(
        title="Wenchuang Agent API",
        description="文创 Agent MVP API：需求解析、风控、检索适配、文化考据、创意设计和营销文案。",
        version="0.1.0",
    )

    @app.middleware("http")
    async def force_utf8_json_response(request, call_next):
        """强制 JSON 响应声明 UTF-8，减少 Windows/PowerShell 中文乱码。"""

        response = await call_next(request)
        content_type = response.headers.get("content-type", "")
        if content_type.startswith("application/json") and "charset=" not in content_type:
            response.headers["content-type"] = "application/json; charset=utf-8"
        return response

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "service": "wenchuang-agent",
            "database": "mock-retriever",
        }

    @app.post("/chat", response_model=WenchuangState)
    async def chat(request: ChatRequest):
        """运行完整文创 Agent，返回结构化状态。"""

        result = await run_agent(request.query)
        return result

    @app.post("/chat/stream")
    async def chat_stream(request: ChatRequest):
        """返回完整 Agent 的最终答案文本流。

        这里是 Agent 跑完后按行输出；真正 token 级 LLM streaming 见 `/llm/stream`。
        """

        from fastapi.responses import StreamingResponse

        async def event_stream():
            result = await run_agent(request.query)
            for line in result.final_answer.splitlines(keepends=True):
                yield line

        return StreamingResponse(event_stream(), media_type="text/plain; charset=utf-8")

    @app.post("/llm/stream")
    async def llm_stream(request: LlmStreamRequest):
        """直接调用统一 LLM 的 streaming 能力。"""

        from fastapi.responses import StreamingResponse

        async def event_stream():
            llm = UnifiedLLM()
            async for chunk in llm.stream_chat(request.system, request.query, temperature=request.temperature):
                yield chunk

        return StreamingResponse(event_stream(), media_type="text/plain; charset=utf-8")

    @app.get("/flow")
    async def flow():
        """返回当前工作流拓扑，方便前端或文档展示。"""

        return {
            "steps": [step.model_dump() for step in FLOW_STEPS],
            "branches": [branch.model_dump() for branch in FLOW_BRANCHES],
        }

    @app.get("/demo-cases", response_model=list[DemoCase])
    async def demo_cases():
        """返回内置演示案例列表。"""

        return DEMO_CASES

    @app.get("/demo-cases/{case_id}", response_model=DemoCase)
    async def get_demo_case(case_id: str):
        """按 ID 查询单个演示案例。"""

        for demo_case in DEMO_CASES:
            if demo_case.id == case_id:
                return demo_case
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"Unknown demo case: {case_id}")

    @app.post("/demo-cases/{case_id}/run", response_model=WenchuangState)
    async def run_demo_case(case_id: str):
        """运行指定演示案例。"""

        for demo_case in DEMO_CASES:
            if demo_case.id == case_id:
                return await run_agent(demo_case.query)
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"Unknown demo case: {case_id}")

    return app


app = create_app()
