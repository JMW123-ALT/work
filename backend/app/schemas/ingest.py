"""
入库相关请求/响应模型
"""
from typing import Literal

from pydantic import BaseModel, Field, model_validator

PermissionLevel = Literal["public", "free", "paid", "internal", "restricted"]
Modality = Literal["text", "pdf", "image", "office"]
IngestRole = Literal["none", "contributor", "internal_uploader", "admin"]


class IngestTextRequest(BaseModel):
    """文本入库（JSON 请求体）"""

    title: str = Field(..., min_length=1, max_length=500, description="文档标题")
    content: str = Field(..., min_length=1, description="文档内容")
    object_type: str = Field(default="internal_doc")
    permission_level: PermissionLevel = Field(default="public")
    access_channel: str = Field(default="web")
    original_ref_uri: str = Field(default="manual://local-entry")
    section_path: str | None = Field(default=None)
    modality: Modality = Field(default="text")
    ingest_role: IngestRole = Field(default="none")
    operator: str = Field(default="local-admin")

    @model_validator(mode="after")
    def _default_section_path(self) -> "IngestTextRequest":
        if not self.section_path:
            self.section_path = self.title
        return self

    @model_validator(mode="after")
    def _no_binary_modality_in_json(self) -> "IngestTextRequest":
        if self.modality in ("pdf", "image", "office"):
            raise ValueError(f"模态 '{self.modality}' 必须使用文件上传接口（/ingest/file）")
        return self


class IngestedItem(BaseModel):
    """单个入库结果"""

    source_id: str
    title: str
    modality: str
    permission_level: str
    chunk_count: int
    file_name: str = ""
    file_size: int = 0
    extraction_status: str = "parsed"

    model_config = {"extra": "allow"}


class IngestResponse(BaseModel):
    item: IngestedItem | None = None
    items: list[IngestedItem] = Field(default_factory=list)
