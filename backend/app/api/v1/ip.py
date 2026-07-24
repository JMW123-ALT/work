"""文创 IP 设计 API 路由。

Endpoints:
  POST /ip/design/chat/stream  — 对话式 IP 形象设计（SSE 流式）
  POST /ip/design/image        — 出图：中文 prompt 转英文 → 文生图 / 图生图
"""
from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.ip.agents import IpDesignAgent
from app.schemas.ip import IpChatRequest, IpImageRequest, IpImageResponse
from app.services.image_generation_client import (
    generate_image_to_image,
    generate_text_to_image,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ip/design", tags=["ip-design"])

_ip_agent = IpDesignAgent()


@router.post("/chat/stream")
async def ip_design_chat_stream(req: IpChatRequest):
    """对话式 IP 形象设计（SSE 流式）。"""
    import json

    request = {"history": [m.model_dump() for m in req.history]}

    async def event_generator():
        try:
            async for line in _ip_agent.stream_run(request):
                yield line
        except Exception as exc:
            logger.error("IpDesignAgent stream error: %s", exc)
            yield f"event: error\ndata: {json.dumps({'message': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _decode_data_url(data_url: str) -> tuple[bytes, str]:
    """把 data URL 或 base64 解成 (bytes, content_type)。"""
    content_type = "image/png"
    b64 = data_url
    if data_url.startswith("data:"):
        header, _, b64 = data_url.partition(",")
        # header 形如 data:image/png;base64
        if ":" in header and ";" in header:
            content_type = header.split(":", 1)[1].split(";", 1)[0] or content_type
    return base64.b64decode(b64), content_type


@router.post("/image", response_model=IpImageResponse)
async def ip_design_image(req: IpImageRequest):
    """出图：先把中文 prompt 转英文，再按 mode 走文生图 / 图生图。"""
    import asyncio

    loop = asyncio.get_event_loop()

    # 中文 prompt → 英文（DeepSeek），失败自动回退中文
    prompt_en = await loop.run_in_executor(
        None, _ip_agent.translate_prompt, req.prompt_cn
    )

    if req.mode == "edit":
        if not req.ref_image.strip():
            raise HTTPException(status_code=400, detail="图生图需要提供参考图")
        try:
            image_bytes, content_type = _decode_data_url(req.ref_image)
        except Exception:
            raise HTTPException(status_code=400, detail="参考图解析失败")
        result = await loop.run_in_executor(
            None,
            lambda: generate_image_to_image(
                model=req.model,
                image_bytes=image_bytes,
                image_filename="ref.png",
                image_content_type=content_type,
                prompt=prompt_en,
                size=req.size,
            ),
        )
    else:
        result = await loop.run_in_executor(
            None,
            lambda: generate_text_to_image(
                model=req.model,
                prompt=prompt_en,
                size=req.size,
                n=req.n,
            ),
        )

    return {
        "prompt_en": prompt_en,
        "images": result.get("images", []) if result else [],
        "model": req.model,
        "mode": req.mode,
    }
