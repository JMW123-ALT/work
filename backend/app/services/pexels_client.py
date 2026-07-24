"""Pexels 图片搜索客户端。

调用 Pexels Photo Search API 检索可用于文章配图的高质量图片。
使用标准库 urllib，无需额外依赖。免费 API：https://www.pexels.com/api/
"""
from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request

from app.core.config import settings

logger = logging.getLogger(__name__)


def search_photos(query: str, per_page: int = 15, page: int = 1) -> dict:
    """按关键词搜索图片，返回归一化结果。

    返回结构：
      {
        "photos": [
          {
            "id": int,
            "thumb": 缩略图 URL（列表展示用）,
            "url": 大图 URL（插入文章用）,
            "alt": 图片描述,
            "photographer": 摄影师署名,
            "source": "pexels",
          }, ...
        ],
        "total": int,
        "provider": "pexels",
      }
    """
    if not settings.pexels_api_key:
        return {"photos": [], "total": 0, "provider": "pexels", "error": "PEXELS_API_KEY 未配置"}

    query = (query or "").strip()
    if not query:
        return {"photos": [], "total": 0, "provider": "pexels"}

    per_page = max(1, min(int(per_page), 40))
    page = max(1, int(page))

    params = urllib.parse.urlencode(
        {"query": query, "per_page": per_page, "page": page}
    )
    url = f"{settings.pexels_base_url.rstrip('/')}/search?{params}"

    try:
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": settings.pexels_api_key,
                "User-Agent": "wenchuang-agent/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=float(settings.pexels_timeout)) as resp:
            raw = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        logger.warning("Pexels search failed: %s", exc)
        return {"photos": [], "total": 0, "provider": "pexels", "error": "图片搜索失败，请稍后重试"}

    photos: list[dict] = []
    for item in raw.get("photos", []):
        src = item.get("src", {}) or {}
        photos.append(
            {
                "id": item.get("id"),
                # 列表缩略图：medium 兼顾清晰度与流量
                "thumb": src.get("medium") or src.get("small") or src.get("tiny", ""),
                # 插入正文用大图：large 已足够，避免超大原图拖慢渲染
                "url": src.get("large") or src.get("original") or src.get("medium", ""),
                "alt": (item.get("alt") or query)[:80],
                "photographer": item.get("photographer", ""),
                "source": "pexels",
            }
        )

    return {
        "photos": photos,
        "total": raw.get("total_results", len(photos)),
        "provider": "pexels",
    }
