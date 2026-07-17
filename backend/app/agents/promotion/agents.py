"""传播类 Agent 扩展口。

以下 Agent 均为未来扩展占位，当前明确抛出 NotImplementedError。
"""

from __future__ import annotations


class XiaohongshuCopyAgent:
    """小红书文案 Agent — 未实现。"""

    agent_code = "xiaohongshu_sub_agent"

    async def run(self, request: dict) -> dict:
        raise NotImplementedError(
            f"Agent '{self.agent_code}' is not yet implemented."
        )


class DouyinCopyAgent:
    """抖音脚本 Agent — 未实现。"""

    agent_code = "douyin_sub_agent"

    async def run(self, request: dict) -> dict:
        raise NotImplementedError(
            f"Agent '{self.agent_code}' is not yet implemented."
        )


class WechatArticleAgent:
    """公众号文章 Agent — 未实现。"""

    agent_code = "wechat_video_sub_agent"

    async def run(self, request: dict) -> dict:
        raise NotImplementedError(
            f"Agent '{self.agent_code}' is not yet implemented."
        )


class VideoScriptAgent:
    """视频号脚本 Agent — 未实现。"""

    agent_code = "video_script_agent"

    async def run(self, request: dict) -> dict:
        raise NotImplementedError(
            f"Agent '{self.agent_code}' is not yet implemented."
        )
