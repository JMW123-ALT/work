"""
文档相关响应模型
"""
from pydantic import BaseModel


class DocumentItem(BaseModel):
    source_id: str
    title: str
    content: str
    object_type: str
    permission_level: str
    access_channel: str
    original_ref_uri: str
    section_path: str
    modality: str = "text"
    file_name: str = ""
    file_path: str = ""
    mime_type: str = ""
    file_size: int = 0
    chunk_count: int = 0
    extraction_status: str = "parsed"
    runtime: int = 0
    created_at: str = ""
    updated_at: str = ""

    model_config = {"extra": "allow"}


class DocumentListResponse(BaseModel):
    items: list[DocumentItem]
