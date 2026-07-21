"""Pydantic schemas for image planning endpoints."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ImagePromptRequest(BaseModel):
    theme: str = Field(..., description="画面主题（必填）")
    style: str = Field(default="", description="画风偏好")
    ratio: str = Field(default="1:1", description="宽高比，如 16:9")
    extra: str = Field(default="", description="补充说明")


class ImagePromptResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    prompt: str
    negative_prompt: str
    style: str
    ratio: str
    model_suggestion: str
    mode: str


class TextToImageRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model: str = Field(..., description="生图模型")
    prompt: str = Field(..., description="正向提示词")
    negative_prompt: str = Field(default="", description="负向提示词（可选）")
    size: str = Field(default="1024x1024", description="图片尺寸，如 1024x1024")
    n: int = Field(default=1, ge=1, le=4, description="生成数量，1-4")
    quality: str = Field(default="", description="质量，如 standard/hd/high；留空则不传")


class ImageResult(BaseModel):
    url: Optional[str] = None
    b64_json: Optional[str] = None
    data_url: Optional[str] = None
    revised_prompt: Optional[str] = None


class ImageGenerationResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    images: list[ImageResult]
    model: str
    provider: str = "8848"


class ImageModelsResponse(BaseModel):
    models: list[str]
    default: str
