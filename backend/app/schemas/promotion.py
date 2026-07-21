"""宣发类接口 schema。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class XiaohongshuRequest(BaseModel):
    subject: str = Field(..., description="活动/景区/产品名称（必填）")
    highlights: str = Field(default="", description="核心亮点，一行一条")
    audience: str = Field(default="", description="目标人群，逗号分隔（可含自定义）")
    tone: str = Field(default="活泼种草", description="语气风格（可含自定义）")
    use_web_search: bool = Field(default=True, description="是否联网参考最新爆款")


class XiaohongshuResponse(BaseModel):
    title: str = Field(description="标题（带 emoji）")
    body: str = Field(description="正文，含分段和 emoji")
    tags: list[str] = Field(default_factory=list, description="话题标签，不含 #")
    full_text: str = Field(description="排版好的完整文案，可直接复制发布")
    references: list[str] = Field(default_factory=list, description="联网参考的爆款标题")
    mode: str = Field(default="deepseek", description="deepseek / placeholder")
