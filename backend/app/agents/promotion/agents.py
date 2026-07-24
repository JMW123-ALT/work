"""传播类 Agent 扩展口。

小红书、公众号文案 Agent 已实现（DeepSeek 流式）；抖音、视频号为占位。
"""

from __future__ import annotations

import logging
import re


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
    """抖音短视频脚本 Agent — DeepSeek 流式生成，输出标语/大纲/分镜/简介四板块。"""

    agent_code = "douyin_sub_agent"

    async def stream_run(self, request: dict):
        """流式生成抖音脚本，async generator，yield SSE 原始行。

        request: subject / duration(秒) / style
        前端按 ===标语===/===大纲===/===分镜===/===简介=== 分段解析。
        """
        import asyncio
        import json as _json

        from app.agents.promotion.prompts import (
            DOUYIN_SYSTEM_PROMPT,
            DOUYIN_USER_TEMPLATE,
        )
        from app.services.llm_client import llm_client

        subject = (request.get("subject") or "").strip()
        duration = request.get("duration") or 30
        style = (request.get("style") or "").strip() or "根据主题自由发挥"

        user_msg = DOUYIN_USER_TEMPLATE.format(
            subject=subject, duration=duration, style=style
        )
        messages = [
            {"role": "system", "content": DOUYIN_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

        yield "event: start\ndata: {}\n\n"

        # 桥接同步流式迭代器到 async
        sentinel = object()
        q: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def _produce() -> None:
            try:
                for chunk in llm_client.stream_chat(
                    messages, temperature=0.85, max_tokens=2500
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

        mode = "deepseek" if llm_client.api_key else "placeholder"
        final_payload = _json.dumps(
            {"raw": accumulated, "mode": mode}, ensure_ascii=False
        )
        yield f"event: final\ndata: {final_payload}\n\n"
        yield "event: done\ndata: {}\n\n"

    async def run(self, request: dict) -> dict:
        """非流式兜底：收集 stream_run 的 final。"""
        import json as _json

        raw, mode = "", "deepseek"
        async for line in self.stream_run(request):
            if line.startswith("event: final"):
                payload = _json.loads(line.split("data:", 1)[1].strip())
                raw = payload.get("raw", "")
                mode = payload.get("mode", "deepseek")
        return {"raw": raw, "mode": mode}


class WechatArticleAgent:
    """公众号文章 Agent — DeepSeek 流式生成 Markdown，正文按标记插入配图。

    配图规则：
      - LLM 在正文合适位置输出 [[IMG: 画面描述]] 标记
      - 每个标记依次消费：优先用用户上传的图片（按上传顺序），
        用完后剩余标记调用文生图生成（若开启 auto_generate）
    """

    agent_code = "wechat_video_sub_agent"

    # 正文里的配图占位标记
    _IMG_RE = re.compile(r"\[\[IMG:\s*(.*?)\]\]", re.DOTALL)

    async def stream_run(self, request: dict):
        """流式生成公众号推文，async generator，yield SSE 原始行。

        request 结构：
          subject/style/article_type/word_count/outline/use_web_search
          uploaded_images: list[dict]  # {"data_url": ..., "name": ...}
          auto_generate: bool          # 是否用文生图补足剩余配图
          image_model: str             # 文生图模型
        """
        import asyncio
        import json as _json

        from app.agents.promotion.prompts import (
            WECHAT_ARTICLE_SYSTEM_PROMPT,
            WECHAT_ARTICLE_USER_TEMPLATE,
        )
        from app.services.llm_client import llm_client
        from app.services.web_search_client import ddg_web_results

        subject = (request.get("subject") or "").strip()
        style = (request.get("style") or "").strip() or "轻松有网感"
        article_type = (request.get("article_type") or "").strip() or "旅游攻略"
        word_count = request.get("word_count") or 1500
        outline = (request.get("outline") or "").strip()
        use_web = bool(request.get("use_web_search", False))
        uploaded = list(request.get("uploaded_images") or [])
        auto_generate = bool(request.get("auto_generate", True))
        image_model = (request.get("image_model") or "gpt-image-2").strip()

        # 配图数量：上传图 + 若开启自动生成再补几张，控制在合理范围
        planned_image_count = len(uploaded) + (3 if auto_generate else 0)
        planned_image_count = max(1, min(planned_image_count, 6)) if (uploaded or auto_generate) else 0

        loop = asyncio.get_event_loop()

        # 联网参考爆款（失败不阻断）
        references: list[str] = []
        web_context = ""
        if use_web:
            hits = await loop.run_in_executor(
                None, ddg_web_results, f"微信公众号 {subject} {article_type} 爆款推文", 6
            )
            references = [h["title"] for h in hits if h.get("title")][:6]
            if references:
                joined = "\n".join(f"- {t}" for t in references)
                web_context = f"\n最近相关的公众号爆款标题参考（模仿风格，不要照抄）：\n{joined}\n"

        outline_block = f"文章大纲（请据此展开）：\n{outline}\n" if outline else ""
        user_msg = WECHAT_ARTICLE_USER_TEMPLATE.format(
            subject=subject,
            style=style,
            article_type=article_type,
            word_count=word_count,
            outline_block=outline_block,
            web_context=web_context,
            image_count=planned_image_count or 2,
        )
        messages = [
            {"role": "system", "content": WECHAT_ARTICLE_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

        yield f"event: start\ndata: {_json.dumps({'planned_images': planned_image_count}, ensure_ascii=False)}\n\n"

        # 桥接同步 LLM 流式迭代器到 async
        sentinel = object()
        q: asyncio.Queue = asyncio.Queue()

        def _produce() -> None:
            try:
                for chunk in llm_client.stream_chat(
                    messages, temperature=0.75, max_tokens=4000
                ):
                    asyncio.run_coroutine_threadsafe(q.put(chunk), loop)
            finally:
                asyncio.run_coroutine_threadsafe(q.put(sentinel), loop)

        loop.run_in_executor(None, _produce)

        # 输出队列：文字 delta、图片 event、final/done 都先放进来，主循环统一 yield。
        # 这样文生图（20~30s）作为后台任务运行，文字继续流，图片好了再单独推送，
        # 不再阻塞标记之后的正文。
        done_marker = object()
        out_q: asyncio.Queue = asyncio.Queue()

        accumulated = ""            # 已发给前端的规范化文本（标记替换为 {{IMG:idx}} 占位）
        upload_cursor = 0           # 下一张要用的上传图下标
        images_by_index: dict[int, dict] = {}  # idx -> 解析后的图片
        img_tasks: list = []        # 后台文生图任务

        def _emit(text: str) -> str:
            data = _json.dumps({"content": text}, ensure_ascii=False)
            return f"event: delta\ndata: {data}\n\n"

        def _image_sse(idx: int, resolved: dict) -> str:
            payload = _json.dumps({"index": idx, **resolved}, ensure_ascii=False)
            return f"event: image\ndata: {payload}\n\n"

        def _resolve_sync_image(desc: str) -> dict | None:
            """立即可得的图片：上传图 / 图库图。没有可用的返回 None（需文生图）。"""
            nonlocal upload_cursor
            if upload_cursor < len(uploaded):
                img = uploaded[upload_cursor]
                upload_cursor += 1
                # 带 data_url 的是用户上传图；仅带 url 的是图库搜索图
                source = "upload" if img.get("data_url") else "stock"
                return {
                    "data_url": img.get("data_url", ""),
                    "url": img.get("url"),
                    "source": source,
                    "alt": desc[:60],
                }
            return None

        async def _generate_image_task(idx: int, desc: str) -> None:
            """后台文生图任务：完成后把图片事件放入输出队列。"""
            from app.services.image_generation_client import generate_text_to_image

            resolved: dict = {}
            prompt = f"微信公众号配图，{article_type}，{style}风格。{desc}。构图精美，高清，杂志感"
            try:
                res = await loop.run_in_executor(
                    None,
                    lambda: generate_text_to_image(
                        model=image_model,
                        prompt=prompt,
                        negative_prompt="低质量、模糊、水印、多余文字",
                        size="1024x1024",
                        n=1,
                    ),
                )
                imgs = res.get("images", []) if res else []
                if imgs:
                    first = imgs[0]
                    resolved = {
                        "data_url": first.get("data_url", ""),
                        "url": first.get("url"),
                        "source": "generated",
                        "alt": desc[:60],
                    }
            except Exception as exc:  # 单图失败不阻断全文
                logging.getLogger("app").warning("wechat image gen failed: %s", exc)
            images_by_index[idx] = resolved
            await out_q.put(_image_sse(idx, resolved))

        async def _driver() -> None:
            """读取 LLM 文本，解析标记，文字即时入队，配图按需后台生成。"""
            nonlocal accumulated
            pending = ""
            img_index = 0
            while True:
                item = await q.get()
                if item is sentinel:
                    break
                pending += item

                # 反复提取 pending 中已完整出现的标记
                while True:
                    m = self._IMG_RE.search(pending)
                    if not m:
                        break
                    before = pending[: m.start()]
                    if before:
                        accumulated += before
                        await out_q.put(_emit(before))
                    desc = m.group(1).strip()
                    idx = img_index
                    placeholder = f"\n\n{{{{IMG:{idx}}}}}\n\n"
                    accumulated += placeholder
                    await out_q.put(_emit(placeholder))

                    sync_img = _resolve_sync_image(desc)
                    if sync_img is not None:
                        # 上传图/图库图：立即推送
                        images_by_index[idx] = sync_img
                        await out_q.put(_image_sse(idx, sync_img))
                    elif auto_generate:
                        # 文生图：占位 + 后台生成，不阻塞文字
                        images_by_index[idx] = {}
                        img_tasks.append(
                            asyncio.create_task(_generate_image_task(idx, desc))
                        )
                    else:
                        images_by_index[idx] = {}
                        await out_q.put(_image_sse(idx, {}))

                    img_index += 1
                    pending = pending[m.end():]

                # 没有完整标记时，保留可能是半个标记的尾巴，其余发出
                safe_upto = self._safe_flush_len(pending)
                if safe_upto > 0:
                    chunk = pending[:safe_upto]
                    accumulated += chunk
                    await out_q.put(_emit(chunk))
                    pending = pending[safe_upto:]

            # LLM 文本结束，冲刷剩余
            if pending:
                accumulated += pending
                await out_q.put(_emit(pending))

            # 等所有后台文生图完成，图片事件已在各任务内推送
            if img_tasks:
                await asyncio.gather(*img_tasks, return_exceptions=True)

            mode = "deepseek" if llm_client.api_key else "placeholder"
            images = [images_by_index.get(i, {}) for i in range(img_index)]
            final_payload = _json.dumps(
                {
                    "markdown": accumulated,
                    "images": images,
                    "references": references,
                    "mode": mode,
                },
                ensure_ascii=False,
            )
            await out_q.put(f"event: final\ndata: {final_payload}\n\n")
            await out_q.put("event: done\ndata: {}\n\n")
            await out_q.put(done_marker)

        driver_task = asyncio.create_task(_driver())
        try:
            while True:
                out = await out_q.get()
                if out is done_marker:
                    break
                yield out
        finally:
            driver_task.cancel()

    @staticmethod
    def _safe_flush_len(buf: str) -> int:
        """返回 buf 中可安全发出的长度，保留可能是未完成 [[IMG 标记的尾巴。

        DeepSeek 逐 token 流式返回，"[[IMG:" 可能被拆分到多个 chunk，
        因此需要同时处理两种情况：
          1) buf 中出现了未闭合的完整开头 "[[IMG:"（完整标记已被上层提取，
             这里剩下的必然是还没等到 "]]" 的），从它起全部保留；
          2) buf 末尾恰好是 "[[IMG:" 的部分前缀（如 "["、"[["、"[[IM"），保留该尾巴。
        """
        marker_open = "[[IMG:"
        pos = buf.find(marker_open)
        if pos != -1:
            return pos
        # 末尾最长的、等于 marker_open 某个前缀的子串
        max_check = min(len(buf), len(marker_open) - 1)
        for cut in range(max_check, 0, -1):
            if marker_open.startswith(buf[-cut:]):
                return len(buf) - cut
        return len(buf)

    async def run(self, request: dict) -> dict:
        """非流式兜底：把 stream_run 的 final 结果收集起来返回。"""
        markdown = ""
        images: list[dict] = []
        references: list[str] = []
        mode = "deepseek"
        async for line in self.stream_run(request):
            if line.startswith("event: final"):
                import json as _json

                data_str = line.split("data:", 1)[1].strip()
                payload = _json.loads(data_str)
                markdown = payload.get("markdown", "")
                images = payload.get("images", [])
                references = payload.get("references", [])
                mode = payload.get("mode", "deepseek")
        return {
            "markdown": markdown,
            "images": images,
            "references": references,
            "mode": mode,
        }


class VideoScriptAgent:
    """视频号脚本 Agent — 未实现。"""

    agent_code = "video_script_agent"

    async def run(self, request: dict) -> dict:
        raise NotImplementedError(
            f"Agent '{self.agent_code}' is not yet implemented."
        )
