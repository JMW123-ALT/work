"""宣发类接口 schema。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class XiaohongshuRequest(BaseModel):
    subject: str = Field(..., description="活动/景区/产品名称（必填）")
    highlights: str = Field(default="", description="核心亮点，一行一条")
    audience: str = Field(default="", description="目标人群，逗号分隔（可含自定义）")
    tone: str = Field(default="活泼种草", description="语气风格（可含自定义）")
    use_web_search: bool = Field(default=True, description="是否联网参考最新爆款")


class DouyinRequest(BaseModel):
    subject: str = Field(..., description="视频主题（必填）")
    duration: int = Field(default=30, ge=5, le=600, description="视频时长（秒）")
    style: str = Field(default="", description="视频风格（可选，可自定义）")


class XiaohongshuResponse(BaseModel):
    title: str = Field(description="标题（带 emoji）")
    body: str = Field(description="正文，含分段和 emoji")
    tags: list[str] = Field(default_factory=list, description="话题标签，不含 #")
    full_text: str = Field(description="排版好的完整文案，可直接复制发布")
    references: list[str] = Field(default_factory=list, description="联网参考的爆款标题")
    mode: str = Field(default="deepseek", description="deepseek / placeholder")


class WechatImage(BaseModel):
    data_url: str | None = Field(default=None, description="图片 data URL（base64）")
    url: str | None = Field(default=None, description="图片外链 URL")
    source: str = Field(default="generated", description="upload / generated")
    alt: str = Field(default="", description="图片说明")


class WechatArticleResponse(BaseModel):
    markdown: str = Field(description="Markdown 正文，含 {{IMG:idx}} 图片占位")
    images: list[WechatImage] = Field(default_factory=list, description="按占位顺序的图片列表")
    references: list[str] = Field(default_factory=list, description="联网参考的爆款标题")
    mode: str = Field(default="deepseek", description="deepseek / placeholder")


class StockPhoto(BaseModel):
    id: int | None = Field(default=None, description="图片 ID")
    thumb: str = Field(default="", description="缩略图 URL")
    url: str = Field(default="", description="大图 URL（插入正文用）")
    alt: str = Field(default="", description="图片描述")
    photographer: str = Field(default="", description="摄影师署名")
    source: str = Field(default="pexels", description="图片来源")


class StockSearchResponse(BaseModel):
    photos: list[StockPhoto] = Field(default_factory=list, description="搜索到的图片")
    total: int = Field(default=0, description="结果总数")
    provider: str = Field(default="pexels", description="图片来源提供方")
    error: str | None = Field(default=None, description="错误信息（如有）")
