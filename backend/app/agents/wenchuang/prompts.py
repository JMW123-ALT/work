"""文创 Agent prompt 字符串。

所有 prompt 从 services/agent.py 原样迁移，内容不做任何修改。
"""

# ── 系统级 prompt ─────────────────────────────────────────────────────────────

AGENT_SYSTEM_PROMPT = (
    "你是一个资深文旅与文创策划 Agent，擅长基于已入库资料做文化考据、"
    "空间/产品/活动方案设计和传播文案。必须严格依据提供的 evidence，"
    "不得编造资料来源；资料不足时要明确提示。输出中文，结构清晰，可落地。"
)

# ── llm_intent_node prompt 模板（用 {user_query} 格式化） ────────────────────

LLM_INTENT_PROMPT_TEMPLATE = (
    "请做文创/文旅需求解析，并只输出 JSON，不要 Markdown。\n"
    "JSON 字段：intent、keywords、style。\n"
    "intent 只能是 ip_design、exhibition、copywriting、qa、planning。\n"
    "用户需求：{user_query}"
)

# ── cultural_review_node prompt 模板 ─────────────────────────────────────────

CULTURAL_REVIEW_PROMPT_TEMPLATE = (
    "请基于 evidence 做文化考据/项目依据梳理。\n"
    "要求：只使用 evidence，不编造；输出包括：资料依据、可用元素、谨慎点、人工核验点。\n"
    "用户需求：{user_query}\n"
    "当前意图：{intent}\n"
    "风险提示：{warnings}\n\n"
    "evidence：\n{evidence}"
)

# ── design_node prompt 模板 ──────────────────────────────────────────────────

DESIGN_PROMPT_TEMPLATE = (
    "请基于 evidence 和文化考据输出方案设计。\n"
    "如果是公园/景区/概念方案，请输出：项目定位、主题结构、空间/游线、业态活动、运营建议、落地优先级。\n"
    "如果是文创产品，请输出：产品定位、设计语言、视觉元素、工艺建议、落地建议。\n"
    "不得编造 evidence 外的项目事实。\n"
    "用户需求：{user_query}\n"
    "意图：{intent}\n"
    "风格：{style}\n\n"
    "文化考据：\n{cultural_review}\n\n"
    "evidence：\n{evidence}"
)

# ── marketing_node prompt 模板 ───────────────────────────────────────────────

MARKETING_PROMPT_TEMPLATE = (
    "请基于方案设计输出传播文案。\n"
    "要求包括：一句话定位、公众号/小红书文案、短视频口播、电商或招商卖点。"
    "表达要具体，避免空泛。\n"
    "用户需求：{user_query}\n\n"
    "方案设计：\n{design_plan}"
)
