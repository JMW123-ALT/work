"""
搜索和问答相关请求/响应模型
"""
from typing import Any

from pydantic import BaseModel, Field, model_validator

UserType = str


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    user_type: UserType = Field(default="visitor")
    top_k: int = Field(default=5, ge=1, le=50)
    retrieval_top_k: int | None = Field(default=None, ge=1, le=200)
    min_confidence: float = Field(default=0.7, ge=0, le=1)

    @model_validator(mode="after")
    def _default_retrieval_top_k(self) -> "SearchRequest":
        if self.retrieval_top_k is None:
            self.retrieval_top_k = max(self.top_k * 4, self.top_k)
        return self


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_type: UserType = Field(default="visitor")
    top_k: int = Field(default=5, ge=1, le=50)
    retrieval_top_k: int | None = Field(default=None, ge=1, le=200)

    @model_validator(mode="after")
    def _default_retrieval_top_k(self) -> "AskRequest":
        if self.retrieval_top_k is None:
            self.retrieval_top_k = max(self.top_k * 4, self.top_k)
        return self


class RerankMeta(BaseModel):
    mode: str
    model: str


class SearchItem(BaseModel):
    text: str
    source: str
    category: str = ""
    culture_theme: str = ""
    confidence: float = Field(default=0, ge=0, le=1)
    copyright_status: str = "unknown"
    risk_level: str = "low"
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    items: list[SearchItem]
    blockedCount: int = 0
    permissionNotice: str = ""
    rerank: RerankMeta

    model_config = {"populate_by_name": True}


class AskResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]]
    blockedCount: int = 0
    permissionNotice: str = ""
    rerank: RerankMeta
    traceId: str = ""
    mode: str = ""

    model_config = {"populate_by_name": True}
