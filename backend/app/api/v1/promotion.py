"""宣发类 API 路由。

Endpoints:
  POST /promotion/xiaohongshu        — 小红书爆款文案（DeepSeek + 可联网）
  POST /promotion/xiaohongshu/images — 小红书配图（复用文生图 client）
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.promotion.agents import XiaohongshuCopyAgent
from app.schemas.planning_image import ImageGenerationResponse, TextToImageRequest
from app.schemas.promotion import XiaohongshuRequest, XiaohongshuResponse
from app.services.image_generation_client import generate_text_to_image

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/promotion", tags=["promotion"])

_xhs_agent = XiaohongshuCopyAgent()


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
