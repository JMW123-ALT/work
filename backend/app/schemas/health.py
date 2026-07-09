"""
健康检查响应模型
"""
from typing import Any

from pydantic import BaseModel


class VectorStoreStats(BaseModel):
    backend: str = ""
    total: int = 0
    chunks: int = 0
    byPermission: list[dict[str, Any]] = []
    byType: list[dict[str, Any]] = []
    byModality: list[dict[str, Any]] = []

    model_config = {"extra": "allow"}


class HealthResponse(BaseModel):
    status: str
    app: str
    env: str
    collection: str
    vectorStore: dict[str, Any]
