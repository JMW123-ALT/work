"""
应用配置管理
使用 pydantic-settings 实现类型安全的配置加载
"""
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（backend/app/core/ → backend/ → project_root/）
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """应用配置，所有字段均可通过 .env 覆盖"""

    # 应用基础配置
    app_name: str = "Wenchuang Agent API"
    app_env: Literal["local", "dev", "staging", "prod"] = "local"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    debug: bool = Field(default=False, description="调试模式")

    # API 配置
    api_v1_prefix: str = "/api/v1"

    # CORS 配置
    cors_origins: list[str] = Field(default=["*"])
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = Field(default=["*"])
    cors_allow_headers: list[str] = Field(default=["*"])

    # PostgreSQL — v2 data layer
    database_url: str = ""
    database_url_sync: str = ""

    # Default organization for single-org local mode.
    # API layer injects this when no authenticated org context is present.
    # Never hard-code this UUID in business logic; always read settings.
    default_organization_id: str = "00000000-0000-4000-8000-00000000a001"

    # Redis / Celery — present for future use; NOT required for local mode.
    # The current runtime uses FastAPI BackgroundTasks instead of Celery.
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # DeepSeek LLM 配置（回答问题）
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # 阿里 DashScope Embedding 配置
    # EMBEDDING_PROVIDER=dashscope 时启用真实 embedding
    # API key 填写后自动切换，留空则使用本地 ngram 占位
    embedding_provider: str = "dashscope"
    embedding_api_key: str = ""
    embedding_base_url: str = "https://dashscope.aliyuncs.com/api/v1"
    embedding_dashscope_url: str = "https://dashscope.aliyuncs.com/api/v1"
    embedding_model: str = "qwen3-vl-embedding"

    # 阿里 DashScope Rerank 配置
    # RERANK_PROVIDER=dashscope 时启用真实 rerank
    rerank_provider: str = "passthrough"
    rerank_enabled: bool = False
    rerank_api_key: str = ""
    rerank_base_url: str = "https://dashscope.aliyuncs.com/api/v1"
    rerank_model: str = "qwen3-vl-rerank"

    # 文件解析 / OCR 配置
    # PDF/Office 优先使用本地解析库；图片和扫描版 PDF 可选接入 DashScope OCR/VL 模型
    parser_max_chars: int = 200_000
    parser_ocr_provider: str = "none"
    parser_ocr_api_key: str = ""
    parser_ocr_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    parser_ocr_model: str = "qwen-vl-ocr"
    parser_ocr_timeout: int = 60

    # Chroma 向量数据库配置：单后端直接读取本地 backend/data/chroma
    chroma_collection: str = "wenchuang_knowledge"
    chroma_collection_v2: str = "wenchuang_knowledge_v2"
    chroma_path: Path = Field(
        default_factory=lambda: PROJECT_ROOT / "backend" / "data" / "chroma"
    )
    chroma_distance_space: Literal["l2", "ip", "cosine"] = "cosine"
    chroma_local_embedding_dimension: int = 1024

    # 数据目录（运行时确保存在）
    data_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "backend" / "data")
    upload_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "backend" / "data" / "uploads")
    asset_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "backend" / "data" / "assets")

    # 图片生成 API（8848，OpenAI-compatible）
    image_api_base_url: str = "https://api.884819.xyz/v1"
    image_api_key: str = ""
    image_api_timeout: int = 180
    image_api_default_model: str = "gpt-image-2"
    image_api_models: str = (
        "gemini-3.1-flash-image,gpt-image-2,grok-imagine-image,grok-imagine-image-quality"
    )

    # 日志配置
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "text"

    @field_validator("data_dir", "upload_dir", "asset_dir", "chroma_path", mode="before")
    @classmethod
    def resolve_project_relative_paths(cls, v: Path | str) -> Path:
        path = Path(v)
        if path.is_absolute():
            return path
        return PROJECT_ROOT / path

    @field_validator("data_dir", "upload_dir", "asset_dir", "chroma_path", mode="after")
    @classmethod
    def ensure_dirs_exist(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
