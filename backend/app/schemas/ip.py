"""文创 IP 设计接口 schema。"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    role: str = Field(description="user / assistant")
    content: str = Field(description="消息内容")


class IpChatRequest(BaseModel):
    history: list[ChatMessage] = Field(
        default_factory=list, description="完整对话历史（含最新用户输入）"
    )


class IpImageRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model: str = Field(..., description="生图模型")
    prompt_cn: str = Field(..., description="中文文生图提示词（后端转英文后出图）")
    mode: str = Field(default="text", description="text=文生图；edit=图生图")
    ref_image: str = Field(
        default="", description="图生图参考图 data URL 或外链（mode=edit 时使用）"
    )
    size: str = Field(default="1024x1024", description="图片尺寸")
    n: int = Field(default=1, ge=1, le=4, description="生成数量")


class IpImageResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    prompt_en: str = Field(description="实际喂给模型的英文提示词")
    images: list[dict] = Field(default_factory=list, description="生成的图片")
    model: str = ""
    mode: str = "text"
