"""打印当前文创 Agent 的流程说明。

这个脚本不运行模型，只用于在终端快速查看流程节点和异常分支。
"""

FLOW_STEPS = [
    ("START", "用户输入需求"),
    ("intent", "需求解析：识别任务类型、关键词、风格"),
    ("pre_guardrails", "前置风控：拦截文化安全高风险输入"),
    ("retrieve", "检索适配层：当前使用 Mock，后续替换为同事数据库"),
    ("post_guardrails", "后置风控：检查证据版权和风险等级"),
    ("cultural_review", "文化考据：输出溯源、可用元素、慎用点、人工核验点"),
    ("design", "创意设计：输出产品定位、款式、视觉元素和工艺建议"),
    ("marketing", "营销优化：输出小红书、抖音、电商卖点"),
    ("final", "最终输出：汇总状态、风险、证据和生成结果"),
    ("END", "流程结束"),
]


def main() -> None:
    """按顺序输出流程节点和关键分支。"""

    print("文创 Agent 当前流程\n")
    for index, (node, description) in enumerate(FLOW_STEPS, start=1):
        print(f"{index:02d}. {node}: {description}")

    print("\n关键异常分支")
    print("- pre_guardrails -> final: 命中文化安全高风险，直接 blocked")
    print("- retrieve -> cultural_review -> final: 无高置信度史料，need_more_material")
    print("- post_guardrails -> cultural_review: 版权或风险需人工复核，need_human_review")
    print("- cultural_review -> design: 资料足够且未拦截，继续生成方案")


if __name__ == "__main__":
    main()
