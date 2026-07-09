"""Prompt 文件加载工具。"""

from __future__ import annotations

from .settings import get_settings


def load_prompt(name: str) -> str:
    """按名称读取 `wc_agent/prompts/<name>.md`。"""

    path = get_settings().prompt_dir / f"{name}.md"
    return path.read_text(encoding="utf-8")
