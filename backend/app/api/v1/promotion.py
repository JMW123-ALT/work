"""宣发类 API 路由。

Endpoints:
  POST /promotion/xiaohongshu        — 小红书爆款文案（DeepSeek + 可联网）
  POST /promotion/xiaohongshu/images — 小红书配图（复用文生图 client）
  POST /promotion/wechat/stream      — 公众号推文流式生成（含配图）
  GET  /promotion/images/search      — 图片搜索（Pexels）
"""
from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.agents.promotion.agents import (
    DouyinCopyAgent,
    WechatArticleAgent,
    XiaohongshuCopyAgent,
)
from app.schemas.planning_image import ImageGenerationResponse, TextToImageRequest
from app.schemas.promotion import (
    DouyinRequest,
    StockSearchResponse,
    XiaohongshuRequest,
    XiaohongshuResponse,
)
from app.services.image_generation_client import generate_text_to_image
from app.services.pexels_client import search_photos

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/promotion", tags=["promotion"])

_xhs_agent = XiaohongshuCopyAgent()
_wechat_agent = WechatArticleAgent()
_douyin_agent = DouyinCopyAgent()

_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 单张上传图 10MB
_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/xiaohongshu", response_model=XiaohongshuResponse)
async def generate_xiaohongshu(req: XiaohongshuRequest):
    """生成小红书爆款文案。"""
    try:
        result = await _xhs_agent.run(req.model_dump())
    except Exception as exc:
        logger.error("XiaohongshuCopyAgent error: %s", exc)
        raise HTTPException(status_code=500, detail=f"文案生成失败：{exc}")
    return result


@router.post("/xiaohongshu/stream")
async def generate_xiaohongshu_stream(req: XiaohongshuRequest):
    """流式生成小红书文案（SSE）。"""
    import json

    async def event_generator():
        try:
            async for line in _xhs_agent.stream_run(req.model_dump()):
                yield line
        except Exception as exc:
            logger.error("XiaohongshuCopyAgent stream error: %s", exc)
            yield f"event: error\ndata: {json.dumps({'message': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/douyin/stream")
async def generate_douyin_stream(req: DouyinRequest):
    """流式生成抖音短视频脚本（SSE）。"""
    import json

    async def event_generator():
        try:
            async for line in _douyin_agent.stream_run(req.model_dump()):
                yield line
        except Exception as exc:
            logger.error("DouyinCopyAgent stream error: %s", exc)
            yield f"event: error\ndata: {json.dumps({'message': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/wechat/stream")
async def generate_wechat_stream(
    subject: str = Form(...),
    style: str = Form(default=""),
    article_type: str = Form(default=""),
    word_count: int = Form(default=1500),
    outline: str = Form(default=""),
    use_web_search: bool = Form(default=False),
    auto_generate: bool = Form(default=True),
    image_model: str = Form(default="gpt-image-2"),
    stock_images: str = Form(default=""),
    images: list[UploadFile] = File(default=[]),
):
    """流式生成公众号推文（SSE），支持上传配图 + 搜索配图 + 文生图补足。"""
    import json

    # 读取上传图片，转成 data URL 交给 Agent（顺序即插图顺序）
    uploaded_images: list[dict] = []
    for up in images or []:
        if up.content_type not in _ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"不支持的图片格式 {up.content_type}，仅接受 jpeg/png/webp",
            )
        content = await up.read()
        if len(content) > _MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="单张图片大小超过 10MB 限制")
        b64 = base64.b64encode(content).decode("ascii")
        mime = up.content_type or "image/png"
        uploaded_images.append(
            {"data_url": f"data:{mime};base64,{b64}", "name": up.filename or "upload"}
        )

    # 搜索得到的图片（Pexels 等），以 URL 形式追加到配图列表，插图顺序在上传图之后
    if stock_images.strip():
        try:
            for item in json.loads(stock_images):
                url = (item or {}).get("url", "").strip()
                if url:
                    uploaded_images.append({"url": url, "name": item.get("alt", "stock")})
        except (json.JSONDecodeError, TypeError, AttributeError):
            logger.warning("stock_images 解析失败，已忽略")

    request = {
        "subject": subject,
        "style": style,
        "article_type": article_type,
        "word_count": word_count,
        "outline": outline,
        "use_web_search": use_web_search,
        "auto_generate": auto_generate,
        "image_model": image_model,
        "uploaded_images": uploaded_images,
    }

    async def event_generator():
        try:
            async for line in _wechat_agent.stream_run(request):
                yield line
        except Exception as exc:
            logger.error("WechatArticleAgent stream error: %s", exc)
            yield f"event: error\ndata: {json.dumps({'message': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/xiaohongshu/images", response_model=ImageGenerationResponse)
async def generate_xiaohongshu_images(req: TextToImageRequest):
    """小红书配图：复用文生图 client 出图。"""
    result = generate_text_to_image(
        model=req.model,
        prompt=req.prompt,
        negative_prompt=req.negative_prompt,
        size=req.size,
        n=req.n,
        quality=req.quality,
    )
    return result


@router.get("/images/search", response_model=StockSearchResponse)
async def search_images(
    query: str = Query(..., min_length=1, description="搜索关键词"),
    per_page: int = Query(default=15, ge=1, le=40, description="每页数量"),
    page: int = Query(default=1, ge=1, description="页码"),
):
    """图片搜索：调用 Pexels，返回可插入文章的图片列表。"""
    import asyncio

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, lambda: search_photos(query, per_page=per_page, page=page)
    )
    return result
