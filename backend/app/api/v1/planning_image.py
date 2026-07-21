"""图片方案生成 API 路由。

Endpoints:
  GET  /planning/image/models          — 可用模型列表
  POST /planning/image/prompt          — 提示词生成（DeepSeek）
  POST /planning/image/text-to-image   — 文生图（ccode API）
  POST /planning/image/image-to-image  — 图生图（ccode /v1/images/edits）
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.agents.planning.agents import ImagePromptAgent
from app.core.config import settings
from app.schemas.planning_image import (
    ImageGenerationResponse,
    ImageModelsResponse,
    ImagePromptRequest,
    ImagePromptResponse,
    TextToImageRequest,
)
from app.services.image_generation_client import (
    generate_image_to_image,
    generate_text_to_image,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/planning/image", tags=["planning-image"])

_agent = ImagePromptAgent()

_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.get("/models", response_model=ImageModelsResponse)
def list_image_models():
    models = [m.strip() for m in settings.image_api_models.split(",") if m.strip()]
    return {"models": models, "default": settings.image_api_default_model}


@router.post("/prompt", response_model=ImagePromptResponse)
async def generate_image_prompt(req: ImagePromptRequest):
    try:
        result = await _agent.run(req.model_dump())
    except Exception as exc:
        logger.error("ImagePromptAgent error: %s", exc)
        raise HTTPException(status_code=500, detail=f"提示词生成失败：{exc}")
    return result


@router.post("/text-to-image", response_model=ImageGenerationResponse)
async def text_to_image(req: TextToImageRequest):
    result = generate_text_to_image(
        model=req.model,
        prompt=req.prompt,
        negative_prompt=req.negative_prompt,
        size=req.size,
        n=req.n,
        quality=req.quality,
    )
    return result


@router.post("/image-to-image", response_model=ImageGenerationResponse)
async def image_to_image(
    image: UploadFile = File(...),
    model: str = Form(...),
    prompt: str = Form(...),
    negative_prompt: str = Form(default=""),
    strength: float = Form(default=0.75),
    size: str = Form(default="1024x1024"),
):
    """图生图：调用 ccode /v1/images/edits。"""
    if image.content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"不支持的图片格式 {image.content_type}，仅接受 jpeg/png/webp",
        )
    content = await image.read()
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="图片大小超过 10MB 限制")

    result = generate_image_to_image(
        model=model,
        image_bytes=content,
        image_filename=image.filename or "image.png",
        image_content_type=image.content_type,
        prompt=prompt,
        negative_prompt=negative_prompt,
        size=size,
    )
    return result
