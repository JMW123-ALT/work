"""文创 Agent 风控逻辑。

HIGH_RISK_INPUT_TERMS / PROTECTED_IP_TERMS / ALLOWED_COPYRIGHT_STATUSES
仅文创 Agent 使用，不提升到 agents/common/guardrails.py。
"""

from __future__ import annotations

from app.agents.wenchuang.state import (
    STATUS_BLOCKED,
    STATUS_NEED_HUMAN_REVIEW,
    STATUS_NEED_MORE_MATERIAL,
    WenchuangState,
)


# ── 风控常量 ─────────────────────────────────────────────────────────────────

ALLOWED_COPYRIGHT_STATUSES = {"public_domain", "authorized"}

HIGH_RISK_INPUT_TERMS = (
    "恶搞烈士",
    "侮辱烈士",
    "篡改历史",
    "历史虚无主义",
    "低俗化",
    "丑化传统文化",
    "辱华",
)

PROTECTED_IP_TERMS = (
    "迪士尼",
    "漫威",
    "哈利波特",
    "宝可梦",
    "知名ip",
    "ip联名",
    "商用ip",
)


# ── 节点函数 ─────────────────────────────────────────────────────────────────

def pre_guardrails_node(state: WenchuangState) -> None:
    """前置风控：命中高风险词则 blocked，疑似商用 IP 则需人工复核。"""
    from app.agents.wenchuang.utils import _has_any

    if _has_any(state.user_query, HIGH_RISK_INPUT_TERMS):
        state.status = STATUS_BLOCKED
        state.warnings.append(
            "命中文化安全高风险表达，已停止生成；请调整为尊重史实和传统文化的需求。"
        )
        return

    if _has_any(state.user_query, PROTECTED_IP_TERMS):
        state.status = STATUS_NEED_HUMAN_REVIEW
        state.warnings.append("输入疑似包含受保护商用 IP，最终方案必须进行版权/授权人工复核。")


def post_guardrails_node(state: WenchuangState) -> None:
    """后置风控：检查 evidence 的版权状态和风险等级。"""
    if state.status == STATUS_NEED_MORE_MATERIAL:
        return

    for item in state.evidence:
        if item.copyright_status not in ALLOWED_COPYRIGHT_STATUSES:
            state.status = STATUS_NEED_HUMAN_REVIEW
            state.warnings.append(
                f"证据 {item.source or 'unknown'} 版权状态为 {item.copyright_status}，需授权复核。"
            )
        if item.risk_level in {"medium", "high"}:
            state.status = STATUS_NEED_HUMAN_REVIEW
            state.warnings.append(
                f"证据 {item.source or 'unknown'} 风险等级为 {item.risk_level}，需人工复核。"
            )
        if item.metadata.get("is_controversial"):
            state.status = STATUS_NEED_HUMAN_REVIEW
            state.warnings.append(
                f"证据 {item.source or 'unknown'} 标记为争议资料，需补充多方观点并人工核验。"
            )
