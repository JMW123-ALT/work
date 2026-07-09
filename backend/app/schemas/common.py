"""
统一 API 响应格式基础模型
"""
from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error: str
    message: str
    path: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "validation_error",
                "message": "query is required",
                "path": "/api/v1/search",
            }
        }
    }


class PaginationMeta(BaseModel):
    total: int
    page: int = 1
    page_size: int = 20
    has_more: bool
