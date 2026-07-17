"""文创 Agent fallback 生成函数。

当 LLM 返回占位内容或调用失败时，由这些函数生成基于规则的草稿回答。
"""

from __future__ import annotations

from app.agents.wenchuang.state import WenchuangState
from app.agents.wenchuang.utils import (
    _detect_product,
    _format_evidence_for_prompt,
    _join_or_default,
    _short_text,
    _unique,
)


def _fallback_cultural_review(state: WenchuangState) -> str:
    themes = _unique(item.culture_theme for item in state.evidence if item.culture_theme)
    source_lines = [
        f"- {item.culture_theme or item.category or '资料'}：{_short_text(item.text)}（来源：{item.source or 'unknown'}）"
        for item in state.evidence[:5]
    ]
    caution = "；".join(state.warnings) if state.warnings else "当前未发现重大文化安全或版权风险。"
    return "\n".join(
        [
            "文化溯源与可用元素：",
            *(source_lines or ["- 已检索到可参考素材，但主题字段仍需补全。"]),
            f"建议主线：围绕{_join_or_default(themes, '检索到的资料主题')}提炼空间、产品、活动和叙事线索。",
            f"慎用与核验点：{caution}",
        ]
    )


def _fallback_design_plan(state: WenchuangState) -> str:
    product = _detect_product(state.user_query)
    themes = _join_or_default(
        _unique(item.culture_theme for item in state.evidence if item.culture_theme),
        "已检索资料",
    )
    style = state.style if state.style != "未指定" else "文旅项目现代化表达"
    return "\n".join(
        [
            "方案设计：",
            f"1. 项目定位：以{themes}为依据，形成{product}方向。",
            f"2. 设计语言：采用{style}，保留资料中的真实项目信息。",
            "3. 空间/产品结构：从检索资料中提取主题、节点、游线和运营场景。",
            "4. 落地建议：优先选择可实施、可运营、可传播的模块。",
            "5. 合规要求：落地前复核资料、版权授权和争议内容。",
        ]
    )


def _fallback_marketing_copy(state: WenchuangState) -> str:
    product = _detect_product(state.user_query)
    themes = _join_or_default(
        _unique(item.culture_theme for item in state.evidence if item.culture_theme),
        "项目资料",
    )
    return "\n".join(
        [
            "传播文案：",
            f"一句话定位：基于{themes}，打造可游、可停留、可传播的{product}。",
            f"小红书文案：把{themes}带进日常体验，用一条路线、一个场景或一件产品讲清楚项目价值。",
            "短视频口播：走进这个项目，看见城市与自然重新连接的方式。",
            "推广卖点：资料依据清晰；场景可落地；适合文旅消费、亲子活动和公共空间运营。",
        ]
    )
