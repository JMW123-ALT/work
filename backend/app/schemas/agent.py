"""文创 Agent 请求模型。"""

from pydantic import BaseModel, Field, model_validator


class AgentChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    user_type: str = Field(default="visitor")
    top_k: int = Field(default=5, ge=1, le=50)
    min_confidence: float = Field(default=0.7, ge=0, le=1)

    @model_validator(mode="after")
    def _strip_query(self) -> "AgentChatRequest":
        self.query = self.query.strip()
        if not self.query:
            raise ValueError("query is required")
        return self
