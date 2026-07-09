"""运行配置读取。

项目优先从工作目录下的 `.env` 读取配置，再退回到默认值。
这样 DeepSeek Key、Chroma 路径等敏感/环境相关信息不会写死在代码里。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"
PARENT_ENV_PATH = ROOT_DIR.parent / ".env"
PATH_LIKE_KEYS = {"CHROMA_PATH", "MOCK_KNOWLEDGE_PATH"}


def _load_env_file(path: Path = ENV_PATH) -> None:
    """轻量读取 `.env` 文件。

    这里没有额外引入 python-dotenv，避免多一个依赖；只支持简单的 KEY=VALUE。
    """

    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.lstrip("\ufeff").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key in PATH_LIKE_KEYS and value:
            candidate = Path(value)
            if not candidate.is_absolute():
                value = str((path.parent / candidate).resolve())
        if key and key not in os.environ:
            os.environ[key] = value


_load_env_file(ENV_PATH)
_load_env_file(PARENT_ENV_PATH)


@dataclass(frozen=True)
class Settings:
    """项目运行配置。

    每次调用 `get_settings()` 都会根据当前环境变量创建一份不可变配置对象。
    """

    # 用 default_factory 而不是类定义时直接读 os.getenv，避免测试或启动脚本修改环境变量后不生效。
    llm_api_key: str | None = field(default_factory=lambda: os.getenv("LLM_API_KEY"))
    llm_base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", "https://api.deepseek.com").rstrip("/"))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "deepseek-v4-flash"))
    retriever_provider: str = field(default_factory=lambda: os.getenv("RETRIEVER_PROVIDER", "mock").lower())
    min_confidence: float = field(default_factory=lambda: float(os.getenv("MIN_RETRIEVAL_CONFIDENCE", "0.7")))
    chroma_path: Path = field(default_factory=lambda: Path(os.getenv("CHROMA_PATH", str(ROOT_DIR / ".chroma"))))
    chroma_collection: str = field(default_factory=lambda: os.getenv("CHROMA_COLLECTION", "wenchuang_knowledge"))
    embedding_api_key: str | None = field(default_factory=lambda: os.getenv("EMBEDDING_API_KEY"))
    embedding_base_url: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_BASE_URL", "").rstrip("/")
    )
    embedding_dashscope_url: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_DASHSCOPE_URL", "").rstrip("/")
    )
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "qwen3-vl-embedding"))
    rerank_api_key: str | None = field(default_factory=lambda: os.getenv("RERANK_API_KEY"))
    rerank_base_url: str = field(default_factory=lambda: os.getenv("RERANK_BASE_URL", "").rstrip("/"))
    rerank_model: str = field(default_factory=lambda: os.getenv("RERANK_MODEL", "qwen3-rerank"))
    rerank_enabled: bool = field(default_factory=lambda: os.getenv("RERANK_ENABLED", "false").lower() == "true")
    shujuku_search_url: str = field(
        default_factory=lambda: os.getenv("SHUJUKU_SEARCH_URL", "http://127.0.0.1:8001/api/v1/search")
    )
    shujuku_user_type: str = field(default_factory=lambda: os.getenv("SHUJUKU_USER_TYPE", "visitor"))
    shujuku_search_timeout: float = field(default_factory=lambda: float(os.getenv("SHUJUKU_SEARCH_TIMEOUT", "15")))
    mock_knowledge_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("MOCK_KNOWLEDGE_PATH", str(ROOT_DIR / "wc_agent" / "data" / "sample_knowledge.jsonl"))
        )
    )
    prompt_dir: Path = ROOT_DIR / "wc_agent" / "prompts"


def get_settings() -> Settings:
    """返回当前配置对象。"""

    return Settings()
