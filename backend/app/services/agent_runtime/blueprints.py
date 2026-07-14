"""Agent blueprint registry from the first-stage architecture Prompt.

Blueprints describe the future platform shape. Except for the existing legacy
Wenchuang Agent v1, these entries are not executable business agents yet.
"""

from __future__ import annotations

from app.services.agent_runtime.models import AgentBlueprint


AGENT_BLUEPRINTS: tuple[AgentBlueprint, ...] = (
    AgentBlueprint(
        code="legacy_wenchuang_agent_v1",
        name="现有文创 Agent v1",
        role="legacy",
        phase="current",
        output_artifacts=["final_answer", "evidence"],
        responsibilities=[
            "保留当前 /api/chat 可运行链路",
            "保留 DeepSeek 真实调用",
            "保留资源库检索、qwen3-vl-embedding 和 qwen3-vl-rerank",
        ],
        executable=True,
    ),
    AgentBlueprint(
        code="online_collection_agent",
        name="资料线上收集 Agent",
        role="top_level",
        phase="future",
        output_artifacts=["background_report"],
        responsibilities=[
            "生成检索计划",
            "收集项目资料、政策、新闻、相似案例和数据",
            "调用入库、Chunk、Embedding 和 Rerank",
            "生成带 Evidence 的背景报告",
        ],
    ),
    AgentBlueprint(
        code="planning_outline_agent",
        name="策划大纲 Agent",
        role="top_level",
        phase="future",
        output_artifacts=["outline_candidates", "selected_outline"],
        responsibilities=[
            "完成项目角色系统定位",
            "按红色思维评估和蓝色思维创新生成 2 至 3 个方向",
            "通过 LangGraph interrupt 等待用户选择",
        ],
    ),
    AgentBlueprint(
        code="full_proposal_agent",
        name="策划全稿 Agent",
        role="top_level",
        phase="future",
        output_artifacts=["full_proposal"],
        responsibilities=[
            "根据选定大纲生成全稿",
            "从专家、投资人、政府和运营方视角校验",
            "把事实内容关联到 Evidence",
        ],
    ),
    AgentBlueprint(
        code="proposal_orchestrator_agent",
        name="策划方案统筹 Agent",
        role="top_level",
        phase="future",
        output_artifacts=[
            "presentation_plan",
            "pptx",
            "brochure",
            "chart_spec",
            "generated_image",
        ],
        responsibilities=[
            "统筹 PPT、图表、图片和文件输出工具",
            "不把工具拆成顶级 Agent",
            "进入人工审核前整理交付物",
        ],
    ),
    AgentBlueprint(
        code="cultural_ip_orchestrator_agent",
        name="文创 IP 统筹 Agent",
        role="top_level",
        phase="future",
        output_artifacts=["ip_core_asset", "project_cultural_product"],
        responsibilities=[
            "统筹核心 IP 生成和单项目文创需求",
            "不拆成更多顶级 Agent",
        ],
    ),
    AgentBlueprint(
        code="core_ip_sub_agent",
        name="核心 IP 生成子 Agent",
        role="sub_agent",
        phase="future",
        parent_code="cultural_ip_orchestrator_agent",
        output_artifacts=["ip_core_asset"],
        responsibilities=["生成核心 IP 资产"],
    ),
    AgentBlueprint(
        code="project_cultural_product_sub_agent",
        name="单项目文创子 Agent",
        role="sub_agent",
        phase="future",
        parent_code="cultural_ip_orchestrator_agent",
        output_artifacts=["project_cultural_product"],
        responsibilities=["生成单项目文创产品方案"],
    ),
    AgentBlueprint(
        code="external_output_orchestrator_agent",
        name="对外输出端统筹 Agent",
        role="top_level",
        phase="future",
        output_artifacts=[
            "operation_intelligence",
            "xiaohongshu_content",
            "douyin_script",
            "wechat_article",
            "video_account_script",
        ],
        responsibilities=[
            "统筹运营前置情报和各平台内容输出",
            "不把平台 Agent 拆成新的顶级 Agent",
        ],
    ),
    AgentBlueprint(
        code="operation_intelligence_sub_agent",
        name="运营前置情报子 Agent",
        role="sub_agent",
        phase="future",
        parent_code="external_output_orchestrator_agent",
        output_artifacts=["operation_intelligence"],
        responsibilities=["生成运营前置情报"],
    ),
    AgentBlueprint(
        code="xiaohongshu_sub_agent",
        name="小红书运营子 Agent",
        role="sub_agent",
        phase="future",
        parent_code="external_output_orchestrator_agent",
        output_artifacts=["xiaohongshu_content"],
        responsibilities=["生成小红书内容"],
    ),
    AgentBlueprint(
        code="douyin_sub_agent",
        name="抖音运营子 Agent",
        role="sub_agent",
        phase="future",
        parent_code="external_output_orchestrator_agent",
        output_artifacts=["douyin_script"],
        responsibilities=["生成抖音脚本"],
    ),
    AgentBlueprint(
        code="wechat_video_sub_agent",
        name="视频号/公众号子 Agent",
        role="sub_agent",
        phase="future",
        parent_code="external_output_orchestrator_agent",
        output_artifacts=["wechat_article", "video_account_script"],
        responsibilities=["生成公众号文章和视频号脚本"],
    ),
)


class AgentBlueprintService:
    def __init__(self, blueprints: tuple[AgentBlueprint, ...] = AGENT_BLUEPRINTS) -> None:
        self.blueprints = blueprints

    def list_blueprints(self) -> list[dict]:
        return [blueprint.model_dump() for blueprint in self.blueprints]

    def children_of(self, parent_code: str) -> list[dict]:
        return [
            blueprint.model_dump()
            for blueprint in self.blueprints
            if blueprint.parent_code == parent_code
        ]

    def validate(self) -> None:
        codes = [blueprint.code for blueprint in self.blueprints]
        duplicates = sorted({code for code in codes if codes.count(code) > 1})
        if duplicates:
            raise ValueError(f"duplicate agent blueprint codes: {', '.join(duplicates)}")

        known_codes = set(codes)
        missing_parents = sorted(
            {
                blueprint.parent_code
                for blueprint in self.blueprints
                if blueprint.parent_code and blueprint.parent_code not in known_codes
            }
        )
        if missing_parents:
            raise ValueError(
                f"unknown parent agent blueprint codes: {', '.join(missing_parents)}"
            )
