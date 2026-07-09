"""风控节点。

前置风控处理用户输入中的高风险表达；后置风控处理检索证据的版权、
授权和风险等级。这里先用规则实现，后续可以叠加模型审核。
"""

from __future__ import annotations

from typing import Any

from .state import AgentStatus, WenchuangState


BLOCKED_TERMS = ["篡改历史", "恶搞烈士", "低俗化", "历史虚无主义"]
COPYRIGHT_TERMS = ["迪士尼", "故宫联名", "宝可梦", "泡泡玛特", "知名IP"]


def pre_guardrails_node(state: WenchuangState) -> dict[str, Any]:
    """前置风控：在检索和生成前先处理明显不可做的输入。"""

    warnings = list(state.warnings)
    if any(term in state.user_query for term in BLOCKED_TERMS):
        warnings.append("输入命中文化安全高风险表达，已拦截。")
        return {"status": AgentStatus.BLOCKED, "warnings": warnings}
    if any(term in state.user_query for term in COPYRIGHT_TERMS):
        warnings.append("输入疑似包含受保护商用 IP，需要确认授权后才能生成。")
        return {"status": AgentStatus.NEED_HUMAN_REVIEW, "warnings": warnings}
    return {}


def post_guardrails_node(state: WenchuangState) -> dict[str, Any]:
    """后置风控：根据检索证据判断是否需要人工复核。"""

    warnings = list(state.warnings)
    risky_evidence = [item for item in state.evidence if item.copyright_status not in {"public_domain", "authorized"}]
    if risky_evidence:
        warnings.append("部分史料版权状态不是 public_domain/authorized，商用前需复核授权。")
        return {"warnings": dedupe(warnings), "status": AgentStatus.NEED_HUMAN_REVIEW}
    return {"warnings": dedupe(warnings)}


def dedupe(items: list[str]) -> list[str]:
    """保持顺序去重，避免同一风险提示重复出现。"""

    result: list[str] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result
