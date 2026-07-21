"""传播类 Agent 扩展口。

以下 Agent 均为未来扩展占位，当前明确抛出 NotImplementedError。
"""

from __future__ import annotations


class XiaohongshuCopyAgent:
    """小红书文案 Agent — DeepSeek 生成，可联网参考最新爆款。"""

    agent_code = "xiaohongshu_sub_agent"

    async def run(self, request: dict) -> dict:
        import asyncio
        import json
        import re

        from app.agents.promotion.prompts import (
            XIAOHONGSHU_SYSTEM_PROMPT,
            XIAOHONGSHU_USER_TEMPLATE,
        )
        from app.services.llm_client import llm_client
        from app.services.web_search_client import ddg_web_results

        subject = request.get("subject", "")
        highlights = request.get("highlights", "") or "（未提供，请自行发挥）"
        audience = request.get("audience", "") or "大众游客"
        tone = request.get("tone", "活泼种草")
        use_web = request.get("use_web_search", True)

        # 联网参考最新爆款标题（失败不阻断）
        references: list[str] = []
        web_context = ""
        if use_web:
            loop = asyncio.get_event_loop()
            hits = await loop.run_in_executor(
                None, ddg_web_results, f"小红书 {subject} 爆款文案 笔记", 6
            )
            references = [h["title"] for h in hits if h.get("title")][:6]
            if references:
                joined = "\n".join(f"- {t}" for t in references)
                web_context = f"\n最近小红书相关爆款标题参考（模仿其风格，不要照抄）：\n{joined}\n"

        user_msg = XIAOHONGSHU_USER_TEMPLATE.format(
            subject=subject,
            highlights=highlights,
            audience=audience,
            tone=tone,
            web_context=web_context,
        )
        result = llm_client.chat(
            [
                {"role": "system", "content": XIAOHONGSHU_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.8,
            max_tokens=1500,
        )
        raw = result.get("content", "")
        mode = result.get("mode", "deepseek")

        title, body, tags = self._parse(raw, subject, highlights)
        full_text = self._compose(title, body, tags)
        return {
            "title": title,
            "body": body,
            "tags": tags,
            "full_text": full_text,
            "references": references,
            "mode": mode,
        }

    async def stream_run(self, request: dict):
        """流式生成小红书文案，async generator，yield SSE 原始行。"""
        import asyncio
        import json as _json

        from app.agents.promotion.prompts import (
            XIAOHONGSHU_SYSTEM_PROMPT,
            XIAOHONGSHU_USER_TEMPLATE,
        )
        from app.services.llm_client import llm_client
        from app.services.web_search_client import ddg_web_results

        subject = request.get("subject", "")
        highlights = request.get("highlights", "") or "（未提供，请自行发挥）"
        audience = request.get("audience", "") or "大众游客"
        tone = request.get("tone", "活泼种草")
        use_web = request.get("use_web_search", True)

        # 联网参考（与 run() 逻辑相同）
        references: list[str] = []
        web_context = ""
        if use_web:
            loop = asyncio.get_event_loop()
            hits = await loop.run_in_executor(
                None, ddg_web_results, f"小红书 {subject} 爆款文案 笔记", 6
            )
            references = [h["title"] for h in hits if h.get("title")][:6]
            if references:
                joined = "\n".join(f"- {t}" for t in references)
                web_context = f"\n最近小红书相关爆款标题参考（模仿其风格，不要照抄）：\n{joined}\n"

        user_msg = XIAOHONGSHU_USER_TEMPLATE.format(
            subject=subject,
            highlights=highlights,
            audience=audience,
            tone=tone,
            web_context=web_context,
        )
        messages = [
            {"role": "system", "content": XIAOHONGSHU_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

        yield f"event: start\ndata: {{}}\n\n"

        # 用 asyncio.Queue 桥接同步流式迭代器，避免阻塞事件循环
        sentinel = object()
        q: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def _produce() -> None:
            try:
                for chunk in llm_client.stream_chat(
                    messages, temperature=0.8, max_tokens=1500
                ):
                    asyncio.run_coroutine_threadsafe(q.put(chunk), loop)
            finally:
                asyncio.run_coroutine_threadsafe(q.put(sentinel), loop)

        loop.run_in_executor(None, _produce)

        accumulated = ""
        while True:
            item = await q.get()
            if item is sentinel:
                break
            accumulated += item
            data = _json.dumps({"content": item}, ensure_ascii=False)
            yield f"event: delta\ndata: {data}\n\n"

        # 流结束后解析结构，发送 final
        mode = "deepseek" if llm_client.api_key else "placeholder"
        title, body, tags = self._parse(accumulated, subject, highlights)
        full_text = self._compose(title, body, tags)
        final_payload = _json.dumps(
            {
                "title": title,
                "body": body,
                "tags": tags,
                "full_text": full_text,
                "references": references,
                "mode": mode,
            },
            ensure_ascii=False,
        )
        yield f"event: final\ndata: {final_payload}\n\n"
        yield f"event: done\ndata: {{}}\n\n"

    @staticmethod
    def _parse(raw: str, subject: str, highlights: str):
        """纯文本解析：首行=标题，含 # 的行=标签，其余=正文。

        DeepSeek 直接输出成品文案（非 JSON），避免 JSON 转义破坏排版、
        以及字段名泄漏到正文的问题。
        """
        import json
        import re

        text = (raw or "").strip()

        # 清洗可能残留的 markdown 代码块 / JSON 结构标记
        text = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
        # 万一 LLM 仍返回了 JSON，尽力抽取字段还原成纯文本
        if text.startswith("{") and '"title"' in text:
            try:
                parsed = json.loads(text)
                parts = [str(parsed.get("title", "")).strip(), "", str(parsed.get("body", "")).strip()]
                tg = parsed.get("tags", [])
                if isinstance(tg, list) and tg:
                    parts += ["", " ".join(f"#{str(t).lstrip('#').strip()}" for t in tg)]
                text = "\n".join(p for p in parts if p is not None).strip()
            except Exception:
                pass

        lines = [ln.rstrip() for ln in text.split("\n")]
        # 去掉首尾空行
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()

        if not lines:
            # 完全空：本地兜底
            title = f"✨ {subject}｜这个宝藏地必须安利给你！"
            body = "姐妹们，" + subject + "真的绝了！\n\n" + "\n".join(
                f"✅ {h}" for h in highlights.split("\n") if h.strip()
            )
            return title, body, [subject, "文旅推荐", "小红书旅行", "打卡"]

        title = lines[0].strip()

        # 提取标签：从末尾往上找以 # 开头（或整行都是 #标签）的行
        tags: list[str] = []
        body_lines = lines[1:]
        if body_lines:
            last = body_lines[-1].strip()
            if "#" in last:
                tags = [t.strip() for t in re.findall(r"#([^#\s]+)", last)]
                if tags:
                    body_lines = body_lines[:-1]

        body = "\n".join(body_lines).strip()
        if not tags:
            tags = [subject, "文旅推荐", "小红书旅行"]
        return title, body, tags

    @staticmethod
    def _compose(title: str, body: str, tags: list[str]) -> str:
        tag_line = " ".join(f"#{t}" for t in tags)
        return f"{title}\n\n{body}\n\n{tag_line}".strip()


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
