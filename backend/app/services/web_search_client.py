"""轻量联网搜索工具。

从 DuckDuckGo HTML 结果页提取标题/URL/摘要，无需 API key。
供 websearch 路由与宣发类 Agent 复用。
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request


def ddg_web_results(query: str, max_results: int = 6) -> list[dict]:
    """从 DuckDuckGo HTML 搜索结果页提取标题 + URL + 摘要。"""
    url = (
        "https://html.duckduckgo.com/html/?q="
        + urllib.parse.quote_plus(query)
        + "&kl=cn-zh"
    )
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return []

    results: list[dict] = []
    blocks = re.findall(
        r'class="result__title".*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?'
        r'class="result__snippet"[^>]*>(.*?)</span>',
        html,
        re.DOTALL,
    )
    for href, title_html, snippet_html in blocks[:max_results]:
        title = re.sub(r"<[^>]+>", "", title_html).strip()
        snippet = re.sub(r"<[^>]+>", "", snippet_html).strip()
        real_url = href
        if "duckduckgo.com/l/" in href or href.startswith("//"):
            m = re.search(r"uddg=([^&]+)", href)
            if m:
                real_url = urllib.parse.unquote(m.group(1))
        if title and snippet:
            results.append({"title": title, "url": real_url, "snippet": snippet})

    return results
