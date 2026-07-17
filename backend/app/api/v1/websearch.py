"""
联网搜索路由 — SSE 流式
GET /web-search/stream?q=<query>

流程：
1. 调用 DuckDuckGo Instant Answers API 获取摘要（免费，无需 key）
2. 再抓 DuckDuckGo HTML 搜索结果页，提取前若干条标题+摘要
3. 把结果作为上下文传给 DeepSeek，流式返回综合回答
4. 同时把原始搜索结果条目一起返回给前端展示
"""

import asyncio
import json
import re
import urllib.parse
import urllib.request
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services.llm_client import llm_client

router = APIRouter(tags=["联网搜索"])


def _ddg_instant(query: str) -> dict:
    """DuckDuckGo Instant Answers API — 免费，无需 key，返回结构化摘要。"""
    url = (
        "https://api.duckduckgo.com/?q="
        + urllib.parse.quote_plus(query)
        + "&format=json&no_html=1&skip_disambig=1&kl=cn-zh"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}


def _ddg_web_results(query: str, max_results: int = 6) -> list[dict]:
    """
    从 DuckDuckGo HTML 搜索结果页提取标题 + URL + 摘要。
    无需 API key，轻量 fallback。
    """
    url = (
        "https://html.duckduckgo.com/html/?q="
        + urllib.parse.quote_plus(query)
        + "&kl=cn-zh"
    )
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
            )
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return []

    results = []
    # Extract result blocks
    blocks = re.findall(
        r'class="result__title".*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?'
        r'class="result__snippet"[^>]*>(.*?)</span>',
        html,
        re.DOTALL,
    )
    for href, title_html, snippet_html in blocks[:max_results]:
        title = re.sub(r"<[^>]+>", "", title_html).strip()
        snippet = re.sub(r"<[^>]+>", "", snippet_html).strip()
        # DDG redirects — extract real URL
        real_url = href
        if "duckduckgo.com/l/" in href or href.startswith("//"):
            m = re.search(r"uddg=([^&]+)", href)
            if m:
                real_url = urllib.parse.unquote(m.group(1))
        if title and snippet:
            results.append({"title": title, "url": real_url, "snippet": snippet})

    return results


def _build_web_context(instant: dict, web_results: list[dict]) -> str:
    parts = []

    # Instant answer
    abstract = (instant.get("AbstractText") or "").strip()
    if abstract:
        source = instant.get("AbstractSource") or ""
        parts.append(f"【即时摘要 - {source}】\n{abstract}")

    # Web results
    for i, r in enumerate(web_results, 1):
        parts.append(f"[{i}] {r['title']}\n{r['snippet']}\n来源: {r['url']}")

    return "\n\n".join(parts) if parts else ""


@router.get("/web-search/stream", summary="联网搜索（SSE 流式）")
async def web_search_stream(q: str = ""):
    """
    流式联网搜索：先推送搜索结果条目，再流式推送 LLM 综合回答。

    SSE 事件：
      sources  — JSON array，搜索结果条目列表（一次性推送）
      delta    — LLM 回答文字片段
      done     — 结束信号
    """
    query = q.strip()
    if not query:
        async def empty():
            yield _sse("done", {"status": "empty"})
        return StreamingResponse(empty(), media_type="text/event-stream")

    async def event_stream() -> AsyncIterator[str]:
        # Run blocking network calls in executor
        loop = asyncio.get_event_loop()
        instant, web_results = await asyncio.gather(
            loop.run_in_executor(None, _ddg_instant, query),
            loop.run_in_executor(None, _ddg_web_results, query),
        )

        # Push source cards first
        yield _sse("sources", {"items": web_results})

        # Build context and stream LLM answer
        context = _build_web_context(instant, web_results)
        system = (
            "你是一个联网搜索助手，根据下方提供的真实网页搜索结果，"
            "用流畅的中文综合回答用户问题。"
            "回答要有条理，可以适当引用来源编号（如 [1][2]）。"
            "不要凭空编造内容，如果搜索结果不足请如实说明。"
        )
        if context:
            user_msg = f"搜索结果：\n{context}\n\n用户问题：{query}"
        else:
            user_msg = f"没有获取到搜索结果，请基于自身知识回答：{query}"

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ]

        for chunk in llm_client.stream_chat(messages, temperature=0.3, max_tokens=1200):
            yield _sse("delta", {"content": chunk})
            await asyncio.sleep(0)

        yield _sse("done", {"status": "done"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
