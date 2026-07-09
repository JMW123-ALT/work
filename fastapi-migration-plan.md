# FastAPI 中大型项目改造计划

## 文档说明

本文档为旅游向量数据库 Web 服务从原生 `http.server` 迁移到 FastAPI 框架的完整实施计划。适用于中大型生产环境部署。

**目标受众**：代码生成工具（Claude Code 等）或开发人员  
**项目规模**：中大型生产项目  
**迁移策略**：一次性完整重构，建立可扩展的架构基础

---

## 一、核心原则与架构决策

### 1.1 架构原则

1. **关注点分离**：API 层、业务逻辑层、数据访问层明确分离
2. **依赖注入**：使用 FastAPI 的 DI 系统，便于测试和解耦
3. **类型安全**：全面使用 Pydantic 进行请求/响应验证
4. **可观测性**：结构化日志、请求追踪、审计日志
5. **API 版本化**：所有接口使用 `/api/v1/` 前缀，便于未来演进
6. **安全优先**：认证信息通过 Header 传递，非请求体
7. **渐进式异步**：初期使用同步路由，避免过度重构；预留异步扩展空间

### 1.2 关键技术决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 路由风格 | 同步 `def` 路由 | services 层现为同步代码，避免强制异步化 |
| 数据库连接 | SQLite + threading.RLock | MVP 阶段足够，预留连接池升级路径 |
| 配置管理 | `pydantic-settings` | 类型安全、自动校验、与 FastAPI 生态一致 |
| 认证方式 | Header-based（预留 JWT） | 当前基于角色，未来可扩展为 JWT |
| 文件上传 | `UploadFile` + `Form` | FastAPI 标准做法，支持流式上传 |
| 日志 | 结构化日志（JSON） | 便于集中式日志采集和分析 |
| 错误处理 | 全局异常处理器 | 统一错误响应格式 |
| API 文档 | OpenAPI（自动生成） | FastAPI 内置，零成本获得交互式文档 |

### 1.3 不改动的部分

- **`services/` 层**：业务逻辑保持不变（除 embedding、chunking、LLM 客户端）
- **`data/` 目录**：数据存储结构不变
- **前端代码**：`frontend/` 完全不动，仅调整 API 调用路径（如需加 `/v1`）

---

## 二、目标目录结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 应用工厂 + lifespan
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py              # 依赖注入：get_vector_store, get_current_user
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py        # 汇总所有 v1 路由
│   │       ├── health.py        # GET /health, /audit
│   │       ├── documents.py     # GET /documents
│   │       ├── ingest.py        # POST /ingest
│   │       └── rag.py           # POST /search, /ask
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── exceptions.py        # 自定义异常类
│   │   ├── logging.py           # 日志配置
│   │   └── security.py          # 认证/授权工具函数（未来扩展）
│   │
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── request_id.py        # 请求 ID 中间件
│   │   └── logging.py           # 访问日志中间件
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py            # 通用响应模型（统一错误格式）
│   │   ├── health.py            # Health 相关
│   │   ├── document.py          # Document 相关
│   │   ├── ingest.py            # Ingest 请求/响应
│   │   └── rag.py               # Search/Ask 请求/响应
│   │
│   └── services/                # 现有服务层（基本不改）
│       ├── __init__.py
│       ├── audit.py
│       ├── chunking_client.py   # 不改
│       ├── embedding_client.py  # 不改
│       ├── llm_client.py        # 不改
│       ├── permissions.py
│       ├── rag_service.py
│       ├── rerank_client.py     # 不改
│       └── vector_store.py
│
├── core/                        # 旧 core/ 目录（迁移后删除）
├── data/                        # 数据目录（不动）
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # pytest fixtures
│   └── api/
│       └── v1/
│           ├── test_health.py
│           ├── test_ingest.py
│           └── test_rag.py
│
├── frontend/                    # 前端（不动）
├── docs/                        # 文档（不动）
├── .env.example
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
├── run.py                       # 入口文件（替代原 app.py）
└── README.md
```

---

## 三、依赖清单

### 3.1 生产依赖 (`requirements.txt`)

```txt
# FastAPI 核心
fastapi==0.115.0
uvicorn[standard]==0.30.0
pydantic==2.9.0
pydantic-settings==2.5.0

# 文件上传处理
python-multipart==0.0.9

# 现有依赖（保留）
requests==2.32.0
chromadb==0.4.22  # 或你当前使用的版本

# 日志
python-json-logger==2.0.7

# 可选：未来认证扩展
# python-jose[cryptography]==3.3.0
# passlib[bcrypt]==1.7.4
```

### 3.2 开发依赖 (`requirements-dev.txt`)

```txt
-r requirements.txt

# 测试
pytest==8.3.0
pytest-asyncio==0.24.0
httpx==0.27.0  # FastAPI TestClient 依赖

# 代码质量
ruff==0.6.0
mypy==1.11.0

# 开发工具
ipython==8.26.0
```

---

## 四、核心组件实现

### 4.1 配置管理 (`app/core/config.py`)

```python
"""
应用配置管理
使用 pydantic-settings 实现类型安全的配置加载
"""
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    app_name: str = "Tourism Vector API"
    app_env: Literal["local", "dev", "staging", "prod"] = "local"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    debug: bool = Field(default=False, description="调试模式")
    
    # API 配置
    api_v1_prefix: str = "/api/v1"
    
    # CORS 配置
    cors_origins: list[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]
    
    # DeepSeek LLM 配置
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    
    # Embedding 配置
    embedding_provider: str = "local"
    embedding_api_key: str = ""
    embedding_base_url: str = ""
    embedding_model: str = ""
    
    # Rerank 配置
    rerank_provider: str = "passthrough"
    rerank_api_key: str = ""
    rerank_base_url: str = ""
    rerank_model: str = ""
    
    # Chroma 向量数据库配置
    chroma_host: str = "127.0.0.1"
    chroma_port: int = 8001
    chroma_collection: str = "tourism_knowledge_vectors"
    
    # 数据目录配置
    data_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "backend" / "data")
    upload_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "backend" / "data" / "uploads")
    
    # 日志配置
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"
    
    @field_validator("data_dir", "upload_dir", mode="after")
    @classmethod
    def ensure_dirs_exist(cls, v: Path) -> Path:
        """确保目录存在"""
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# 全局配置实例
settings = Settings()
```

<thinking>
Good, I've added the config.py implementation. Now let me continue with exception handling and logging setup.
</thinking>

### 4.2 异常处理 (`app/core/exceptions.py`)

```python
"""
自定义异常类和全局异常处理器
"""
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    """应用基础异常"""
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: dict[str, Any] | None = None
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(self.message)


class PermissionDeniedError(AppException):
    """权限不足异常"""
    def __init__(self, message: str = "权限不足", detail: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class ValidationError(AppException):
    """业务验证异常"""
    def __init__(self, message: str, detail: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class ResourceNotFoundError(AppException):
    """资源未找到异常"""
    def __init__(self, message: str = "资源不存在", detail: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


# 全局异常处理器
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """处理自定义应用异常"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "detail": exc.detail,
            "path": str(request.url.path)
        }
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """处理 ValueError（来自现有 services 层）"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "validation_error",
            "message": str(exc),
            "path": str(request.url.path)
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """处理 FastAPI HTTPException"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": exc.detail,
            "path": str(request.url.path)
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理未捕获的异常"""
    import traceback
    from app.core.logging import logger
    
    logger.error(
        "Unhandled exception",
        extra={
            "path": str(request.url.path),
            "method": request.method,
            "error": str(exc),
            "traceback": traceback.format_exc()
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "服务器内部错误",
            "path": str(request.url.path)
        }
    )
```

### 4.3 日志配置 (`app/core/logging.py`)

```python
"""
结构化日志配置
"""
import logging
import sys
from typing import Any

from pythonjsonlogger import jsonlogger

from app.core.config import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """自定义 JSON 日志格式"""
    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any]
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["app"] = settings.app_name
        log_record["env"] = settings.app_env


def setup_logging() -> logging.Logger:
    """配置全局日志"""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # 移除现有 handlers
    root_logger.handlers.clear()
    
    # 创建 handler
    handler = logging.StreamHandler(sys.stdout)
    
    if settings.log_format == "json":
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(logger)s %(message)s",
            rename_fields={"timestamp": "asctime"}
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    return logging.getLogger("app")


# 全局 logger 实例
logger = setup_logging()
```

### 4.4 请求 ID 中间件 (`app/middleware/request_id.py`)

```python
"""
请求 ID 中间件
为每个请求注入唯一 trace ID，便于日志追踪
"""
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    为每个请求生成唯一 ID：
    - 优先使用客户端传入的 X-Request-ID header
    - 否则自动生成
    - 将 ID 写入响应 header，同时绑定到 request.state
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = (
            request.headers.get("X-Request-ID")
            or f"req-{uuid.uuid4().hex[:12]}"
        )
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

### 4.5 访问日志中间件 (`app/middleware/logging.py`)

```python
"""
HTTP 访问日志中间件
记录请求耗时、状态码等关键指标
"""
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import logger


class AccessLogMiddleware(BaseHTTPMiddleware):
    """记录每个 HTTP 请求的访问日志"""
    
    SKIP_PATHS = {"/api/v1/health"}  # 健康检查不记录，避免日志噪音
    
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)
        
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        
        logger.info(
            "HTTP request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "request_id": getattr(request.state, "request_id", "-"),
                "client_ip": request.client.host if request.client else "-",
            }
        )
        return response
```

---

## 五、Pydantic Schema 层

### 5.1 通用响应格式 (`app/schemas/common.py`)

```python
"""
统一 API 响应格式
所有接口的响应都应基于这些基础模型
"""
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorResponse(BaseModel):
    """统一错误响应"""
    error: str
    message: str
    path: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)
    
    model_config = {"json_schema_extra": {
        "example": {
            "error": "validation_error",
            "message": "query is required",
            "path": "/api/v1/search"
        }
    }}


class PaginationMeta(BaseModel):
    """分页元信息"""
    total: int
    page: int = 1
    page_size: int = 20
    has_more: bool
```

### 5.2 入库 Schema (`app/schemas/ingest.py`)

```python
"""
入库相关请求/响应模型
"""
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# 权限级别枚举
PermissionLevel = Literal["public", "free", "paid", "internal", "restricted"]
# 数据模态枚举
Modality = Literal["text", "pdf", "image", "office"]
# 入库角色枚举
IngestRole = Literal["none", "contributor", "internal_uploader", "admin"]


class IngestTextRequest(BaseModel):
    """文本入库请求（JSON 请求体）"""
    title: str = Field(..., min_length=1, max_length=500, description="文档标题")
    content: str = Field(..., min_length=1, description="文档内容")
    object_type: str = Field(default="internal_doc", description="文档类型")
    permission_level: PermissionLevel = Field(default="public", description="权限级别")
    access_channel: str = Field(default="web", description="访问渠道")
    original_ref_uri: str = Field(default="manual://local-entry", description="原始引用 URI")
    section_path: str | None = Field(default=None, description="章节路径，默认使用标题")
    modality: Modality = Field(default="text", description="内容模态")
    
    # 操作人信息（未来可从 JWT 中提取，当前从请求体中传入）
    ingest_role: IngestRole = Field(default="none", description="入库角色")
    operator: str = Field(default="local-admin", description="操作人标识")

    @model_validator(mode="after")
    def set_section_path_default(self) -> "IngestTextRequest":
        if not self.section_path:
            self.section_path = self.title
        return self
    
    @model_validator(mode="after")
    def validate_text_modality(self) -> "IngestTextRequest":
        if self.modality in ("pdf", "image", "office"):
            raise ValueError(
                f"模态 '{self.modality}' 必须使用文件上传接口（multipart/form-data）"
            )
        return self


class IngestFileFields(BaseModel):
    """文件入库的表单字段（multipart/form-data）"""
    ingest_role: IngestRole = Field(default="none")
    operator: str = Field(default="local-admin")
    permission_level: PermissionLevel = Field(default="public")
    title: str | None = Field(default=None, max_length=500)
    object_type: str = Field(default="internal_doc")
    access_channel: str = Field(default="web")
    source_id: str | None = Field(default=None)


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


class IngestResponse(BaseModel):
    """入库响应"""
    item: IngestedItem | None = None
    items: list[IngestedItem] = Field(default_factory=list)
```

### 5.3 RAG Schema (`app/schemas/rag.py`)

```python
"""
搜索和问答相关请求/响应模型
"""
from typing import Any

from pydantic import BaseModel, Field, field_validator


UserType = str  # "visitor" | "free" | "paid" | "internal" | "admin"


class SearchRequest(BaseModel):
    """语义搜索请求"""
    query: str = Field(..., min_length=1, max_length=1000, description="搜索查询文本")
    user_type: UserType = Field(default="visitor", description="用户类型，影响权限过滤")
    top_k: int = Field(default=5, ge=1, le=50, description="返回结果数量")
    retrieval_top_k: int | None = Field(
        default=None, ge=1, le=200,
        description="初步检索数量，默认为 top_k * 4"
    )
    
    @field_validator("retrieval_top_k", mode="before")
    @classmethod
    def set_retrieval_top_k(cls, v, values):
        if v is None:
            top_k = values.data.get("top_k", 5)
            return max(top_k * 4, top_k)
        return v


class AskRequest(BaseModel):
    """RAG 问答请求"""
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    user_type: UserType = Field(default="visitor", description="用户类型")
    top_k: int = Field(default=5, ge=1, le=50, description="参考文档数量")
    retrieval_top_k: int | None = Field(default=None, ge=1, le=200)


class SourceItem(BaseModel):
    """搜索结果/引用来源"""
    source_id: str
    title: str
    content: str
    score: float = 0.0
    permission_level: str = "public"
    modality: str = "text"
    extra: dict[str, Any] = Field(default_factory=dict)


class RerankMeta(BaseModel):
    """Rerank 元信息"""
    mode: str
    model: str


class SearchResponse(BaseModel):
    """搜索响应"""
    items: list[SourceItem]
    blocked_count: int = Field(default=0, alias="blockedCount")
    permission_notice: str = Field(default="", alias="permissionNotice")
    rerank: RerankMeta
    
    model_config = {"populate_by_name": True}


class AskResponse(BaseModel):
    """问答响应"""
    answer: str
    sources: list[SourceItem]
    blocked_count: int = Field(default=0, alias="blockedCount")
    permission_notice: str = Field(default="", alias="permissionNotice")
    rerank: RerankMeta
    trace_id: str = Field(default="", alias="traceId")
    mode: str = ""
    
    model_config = {"populate_by_name": True}
```

---

## 六、API 层实现

### 6.1 依赖注入 (`app/api/deps.py`)

```python
"""
FastAPI 依赖注入
将 services 层的单例封装为可注入的依赖，便于测试时替换
"""
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.services.audit import AuditStore, audit_store
from app.services.permissions import normalize_ingest_role, normalize_user_type
from app.services.rag_service import RAGService, rag_service
from app.services.vector_store import VectorStore, vector_store


# ── 服务层依赖 ──────────────────────────────────────────────
def get_vector_store() -> VectorStore:
    return vector_store


def get_rag_service() -> RAGService:
    return rag_service


def get_audit_store() -> AuditStore:
    return audit_store


VectorStoreDep = Annotated[VectorStore, Depends(get_vector_store)]
RAGServiceDep = Annotated[RAGService, Depends(get_rag_service)]
AuditStoreDep = Annotated[AuditStore, Depends(get_audit_store)]


# ── 认证依赖（当前简单实现，预留 JWT 扩展） ─────────────────────
def get_user_type(
    x_user_type: Annotated[str | None, Header(alias="X-User-Type")] = None
) -> str:
    """
    从 X-User-Type Header 获取用户类型
    未来可替换为 JWT 解析
    """
    return normalize_user_type(x_user_type or "visitor")


def get_ingest_role(
    x_ingest_role: Annotated[str | None, Header(alias="X-Ingest-Role")] = None
) -> str:
    """
    从 X-Ingest-Role Header 获取入库角色
    未来可替换为 JWT claims 中提取
    """
    return normalize_ingest_role(x_ingest_role or "none")


UserTypeDep = Annotated[str, Depends(get_user_type)]
IngestRoleDep = Annotated[str, Depends(get_ingest_role)]
```

### 6.2 健康检查路由 (`app/api/v1/health.py`)

```python
from fastapi import APIRouter, Request

from app.core.config import settings
from app.api.deps import AuditStoreDep, VectorStoreDep

router = APIRouter(tags=["健康检查"])


@router.get("/health", summary="服务健康检查")
def health_check(vs: VectorStoreDep):
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "collection": settings.chroma_collection,
        "vectorStore": vs.stats(),
    }


@router.get("/audit", summary="最近审计日志")
def get_audit_log(audit: AuditStoreDep, limit: int = 50):
    return {"items": audit.recent(limit=limit)}
```

### 6.3 文档列表路由 (`app/api/v1/documents.py`)

```python
from fastapi import APIRouter

from app.api.deps import VectorStoreDep

router = APIRouter(tags=["文档管理"])


@router.get("/documents", summary="获取所有文档列表")
def list_documents(vs: VectorStoreDep):
    return {"items": vs.list_documents()}
```

### 6.4 入库路由 (`app/api/v1/ingest.py`)

```python
"""
入库路由
- POST /ingest/text   JSON 文本入库
- POST /ingest/file   multipart 文件入库（支持多文件）
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, Form, status
from typing import Annotated

from app.api.deps import AuditStoreDep, IngestRoleDep, VectorStoreDep
from app.core.exceptions import PermissionDeniedError
from app.schemas.ingest import (
    IngestFileFields,
    IngestResponse,
    IngestTextRequest,
    PermissionLevel,
)
from app.services.permissions import can_assign_permission, can_ingest

router = APIRouter(tags=["入库管理"])


def _check_ingest_permission(
    ingest_role: str,
    permission_level: str,
    operator: str,
    title: str,
    audit: AuditStoreDep,
) -> None:
    """权限校验公共逻辑，抛异常则拒绝"""
    if not can_ingest(ingest_role):
        audit.record("ingest_denied", ingest_role, {
            "operator": operator,
            "reason": "role_cannot_upload",
            "title": title,
        })
        raise PermissionDeniedError("当前入库角色没有上传权限。")
    
    if not can_assign_permission(ingest_role, permission_level):
        audit.record("ingest_denied", ingest_role, {
            "operator": operator,
            "reason": "permission_level_too_high",
            "permissionLevel": permission_level,
            "title": title,
        })
        raise PermissionDeniedError("当前入库角色不能创建该权限级别的资料。")


@router.post(
    "/ingest/text",
    status_code=status.HTTP_201_CREATED,
    response_model=IngestResponse,
    summary="文本内容入库（JSON）",
)
def ingest_text(
    req: IngestTextRequest,
    vs: VectorStoreDep,
    audit: AuditStoreDep,
    background_tasks: BackgroundTasks,
):
    _check_ingest_permission(
        req.ingest_role, req.permission_level, req.operator, req.title, audit
    )
    
    item = vs.add_document(req.model_dump())
    
    # 审计日志放 background task，不阻塞响应
    background_tasks.add_task(
        audit.record, "ingest", req.ingest_role, {
            "operator": req.operator,
            "sourceId": item["source_id"],
            "permissionLevel": item["permission_level"],
            "modality": item["modality"],
            "chunkCount": item["chunk_count"],
        }
    )
    
    return IngestResponse(item=item)


@router.post(
    "/ingest/file",
    status_code=status.HTTP_201_CREATED,
    response_model=IngestResponse,
    summary="文件入库（multipart/form-data，支持 PDF/图片/Office）",
)
def ingest_file(
    vs: VectorStoreDep,
    audit: AuditStoreDep,
    background_tasks: BackgroundTasks,
    files: list[UploadFile],
    ingest_role: Annotated[str, Form()] = "none",
    operator: Annotated[str, Form()] = "local-admin",
    permission_level: Annotated[PermissionLevel, Form()] = "public",
    title: Annotated[str | None, Form()] = None,
    object_type: Annotated[str, Form()] = "internal_doc",
    access_channel: Annotated[str, Form()] = "web",
    source_id: Annotated[str | None, Form()] = None,
):
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="至少需要上传一个文件。"
        )
    
    _check_ingest_permission(
        ingest_role, permission_level, operator, title or "", audit
    )
    
    fields = {
        "ingest_role": ingest_role,
        "operator": operator,
        "permission_level": permission_level,
        "title": title,
        "object_type": object_type,
        "access_channel": access_channel,
        "source_id": source_id,
    }
    
    items = []
    for upload in files:
        file_item = {
            "field": "file",
            "filename": upload.filename or "unnamed",
            "content_type": upload.content_type or "",
            "data": upload.file.read(),
        }
        item = vs.add_file_document(fields, file_item)
        items.append(item)
        background_tasks.add_task(
            audit.record, "ingest_file", ingest_role, {
                "operator": operator,
                "sourceId": item["source_id"],
                "permissionLevel": item["permission_level"],
                "modality": item["modality"],
                "fileName": item["file_name"],
                "chunkCount": item["chunk_count"],
            }
        )
    
    return IngestResponse(items=items, item=items[0] if items else None)
```

### 6.5 RAG 路由 (`app/api/v1/rag.py`)

```python
"""
RAG 搜索与问答路由
"""
from fastapi import APIRouter, BackgroundTasks

from app.api.deps import AuditStoreDep, RAGServiceDep
from app.schemas.rag import AskRequest, AskResponse, SearchRequest, SearchResponse

router = APIRouter(tags=["检索与问答"])


@router.post("/search", response_model=SearchResponse, summary="语义检索")
def search(req: SearchRequest, svc: RAGServiceDep):
    result = svc.search(req.model_dump(by_alias=False))
    return result


@router.post("/ask", response_model=AskResponse, summary="RAG 问答")
def ask(req: AskRequest, svc: RAGServiceDep):
    result = svc.ask(req.model_dump(by_alias=False))
    return result
```

### 6.6 路由汇总 (`app/api/v1/router.py`)

```python
"""
v1 路由总入口
所有 v1 子路由在此集中注册
"""
from fastapi import APIRouter

from app.api.v1 import documents, health, ingest, rag

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(documents.router)
api_router.include_router(ingest.router)
api_router.include_router(rag.router)
```

---

## 七、App 工厂与入口

### 7.1 主应用工厂 (`app/main.py`)

```python
"""
FastAPI 应用工厂
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    general_exception_handler,
    http_exception_handler,
    value_error_handler,
)
from app.core.logging import logger
from app.middleware.logging import AccessLogMiddleware
from app.middleware.request_id import RequestIDMiddleware
from fastapi.exceptions import HTTPException


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info(
        "Application starting",
        extra={"env": settings.app_env, "host": settings.app_host, "port": settings.app_port}
    )
    yield
    logger.info("Application shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="旅游知识向量数据库 API",
        docs_url="/api/docs" if settings.app_env != "prod" else None,
        redoc_url="/api/redoc" if settings.app_env != "prod" else None,
        openapi_url="/api/openapi.json" if settings.app_env != "prod" else None,
        lifespan=lifespan,
    )
    
    # ── 中间件（注意顺序，后注册的先执行） ───────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIDMiddleware)
    
    # ── 异常处理器 ────────────────────────────────────────────────
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    # ── API 路由（必须先于静态文件注册） ──────────────────────────────
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    
    # ── 静态文件（最后挂载，避免吃掉 /api 路径） ─────────────────────
    frontend_dir = settings.data_dir.parents[1] / "frontend"
    if frontend_dir.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
    
    return app


# 全局应用实例
app = create_app()
```

### 7.2 启动入口 (`run.py`)

```python
"""
应用启动入口
替代原来的 app.py 中的 main() 函数
"""
import uvicorn

from app.core.config import settings


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "local",
        log_level=settings.log_level.lower(),
        # 生产环境推荐多 worker
        # workers=4,  # 取消注释用于生产
    )
```

---

## 八、Services 层改动说明

### 8.1 改动清单

| 文件 | 改动 | 说明 |
|------|------|------|
| `services/vector_store.py` | **不改** | 同步代码，线程锁保护，MVP 阶段足够 |
| `services/rag_service.py` | **微调** | 接口签名保持不变；将 `ingest_role`/`operator` 从请求体移到 deps |
| `services/permissions.py` | **不改** | 纯函数，无状态，直接复用 |
| `services/audit.py` | **不改** | 同步文件写入，配合 BackgroundTasks 使用 |
| `services/embedding_client.py` | **不改** | — |
| `services/chunking_client.py` | **不改** | — |
| `services/llm_client.py` | **不改** | — |
| `services/rerank_client.py` | **不改** | — |

### 8.2 `vector_store.py` 长期优化路线（可选，不影响当前迁移）

当前：单 SQLite 连接 + `threading.RLock`，`check_same_thread=False`。

**阶段一（MVP 后）**：改为每次操作独立连接，避免锁竞争：

```python
# 当前做法
self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)

# 改为：操作时临时建立连接
def _get_conn(self):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def list_documents(self):
    with self._get_conn() as conn:
        rows = conn.execute("SELECT ...").fetchall()
    return [dict(row) for row in rows]
```

**阶段二（并发高时）**：引入 `sqlalchemy` 连接池，或迁移到 PostgreSQL + asyncpg。

### 8.3 `audit.py` 配合 BackgroundTasks

原来审计日志是同步写入，会轻微阻塞响应。迁移后在路由层用 `BackgroundTasks` 异步化：

```python
# 路由层
background_tasks.add_task(
    audit.record, "search", user_type, {...}
)
```

`audit.py` 本身无需改动，`BackgroundTasks` 会在响应发送后在后台线程执行。

---

## 九、测试框架

### 9.1 测试配置 (`tests/conftest.py`)

```python
"""
pytest fixtures
使用 FastAPI TestClient，所有测试共享一个应用实例
"""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.api.deps import get_vector_store, get_rag_service, get_audit_store


@pytest.fixture(scope="session")
def app():
    """创建测试用 FastAPI 实例"""
    return create_app()


@pytest.fixture(scope="session")
def client(app):
    """同步测试客户端"""
    with TestClient(app) as c:
        yield c
```

### 9.2 健康检查测试 (`tests/api/v1/test_health.py`)

```python
def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "vectorStore" in data
```

### 9.3 入库测试 (`tests/api/v1/test_ingest.py`)

```python
def test_ingest_text_success(client):
    resp = client.post(
        "/api/v1/ingest/text",
        json={
            "title": "测试文档",
            "content": "这是测试内容",
            "ingest_role": "admin",
            "operator": "test-user",
            "permission_level": "public",
        }
    )
    assert resp.status_code == 201
    item = resp.json()["item"]
    assert item["title"] == "测试文档"
    assert item["chunk_count"] >= 1


def test_ingest_text_forbidden(client):
    resp = client.post(
        "/api/v1/ingest/text",
        json={
            "title": "受限文档",
            "content": "内容",
            "ingest_role": "none",  # 无上传权限
        }
    )
    assert resp.status_code == 403


def test_ingest_text_missing_content(client):
    resp = client.post(
        "/api/v1/ingest/text",
        json={"title": "只有标题"}
    )
    assert resp.status_code == 422  # Pydantic 校验失败
```

### 9.4 搜索测试 (`tests/api/v1/test_rag.py`)

```python
def test_search_success(client):
    resp = client.post(
        "/api/v1/search",
        json={"query": "旅游景点", "user_type": "visitor"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "rerank" in data


def test_search_empty_query(client):
    resp = client.post("/api/v1/search", json={"query": ""})
    assert resp.status_code == 422


def test_ask_success(client):
    resp = client.post(
        "/api/v1/ask",
        json={"question": "推荐几个适合家庭出游的景点"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "sources" in data
    assert "traceId" in data
```

---

## 十、迁移执行步骤

以下步骤按顺序执行，每步完成后可独立验证，降低风险。

### Step 1：建立新目录结构

```bash
cd backend
mkdir -p app/api/v1
mkdir -p app/core
mkdir -p app/middleware
mkdir -p app/schemas
mkdir -p tests/api/v1

# 创建 __init__.py
touch app/__init__.py
touch app/api/__init__.py
touch app/api/v1/__init__.py
touch app/core/__init__.py
touch app/middleware/__init__.py
touch app/schemas/__init__.py
touch tests/__init__.py
touch tests/api/__init__.py
touch tests/api/v1/__init__.py
```

### Step 2：迁移 services 层

```bash
# 将现有 services/ 移入 app/ 下
mv services/ app/services/

# 将旧 core/config.py 暂时保留（Step 4 替换）
cp core/config.py app/core/config_old.py
```

### Step 3：写入所有新文件

按本文档各节内容依次创建：

```
app/core/config.py          ← 见 §4.1
app/core/exceptions.py      ← 见 §4.2
app/core/logging.py         ← 见 §4.3
app/middleware/request_id.py ← 见 §4.4
app/middleware/logging.py   ← 见 §4.5
app/schemas/common.py       ← 见 §5.1
app/schemas/ingest.py       ← 见 §5.2
app/schemas/rag.py          ← 见 §5.3
app/api/deps.py             ← 见 §6.1
app/api/v1/health.py        ← 见 §6.2
app/api/v1/documents.py     ← 见 §6.3
app/api/v1/ingest.py        ← 见 §6.4
app/api/v1/rag.py           ← 见 §6.5
app/api/v1/router.py        ← 见 §6.6
app/main.py                 ← 见 §7.1
run.py                      ← 见 §7.2（放 backend/ 根目录）
```

### Step 4：更新 services 内部导入路径

services 层的 import 需要从相对路径改为 `app.` 前缀：

```python
# 旧（services/rag_service.py 里）
from services.audit import audit_store
from services.vector_store import vector_store

# 新
from app.services.audit import audit_store
from app.services.vector_store import vector_store
```

**批量替换命令**：
```bash
cd backend
# macOS/Linux
find app/services -name "*.py" -exec sed -i '' \
  's/from services\./from app.services./g; s/import services\./import app.services./g' {} +

# Windows PowerShell
Get-ChildItem -Recurse -Filter "*.py" -Path "app/services" |
  ForEach-Object {
    (Get-Content $_.FullName) -replace 'from services\.', 'from app.services.' |
    Set-Content $_.FullName
  }
```

### Step 5：安装依赖

```bash
pip install fastapi==0.115.0 uvicorn[standard]==0.30.0 \
    pydantic==2.9.0 pydantic-settings==2.5.0 \
    python-multipart==0.0.9 python-json-logger==2.0.7

# 开发依赖
pip install pytest==8.3.0 httpx==0.27.0 pytest-asyncio==0.24.0
```

### Step 6：验证启动

```bash
cd backend
python run.py
# 期望看到：INFO: Application starting ...
# 访问 http://127.0.0.1:8000/api/docs 确认 OpenAPI 文档加载正常
```

### Step 7：逐接口验证

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# 文本入库
curl -X POST http://localhost:8000/api/v1/ingest/text \
  -H "Content-Type: application/json" \
  -d '{"title":"测试","content":"内容","ingest_role":"admin"}'

# 语义搜索
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query":"旅游景点推荐"}'

# 文件上传
curl -X POST http://localhost:8000/api/v1/ingest/file \
  -F "files=@test.pdf" \
  -F "ingest_role=admin" \
  -F "permission_level=public"
```

### Step 8：运行测试

```bash
cd backend
pytest tests/ -v
```

### Step 9：清理旧文件

```bash
# 确认一切正常后删除旧文件
rm backend/app.py
rm -rf backend/core/       # 旧 core/，已替换为 app/core/
```

### Step 10（可选）：前端 API 路径适配

如果前端请求路径是 `/api/health`，迁移后变为 `/api/v1/health`。

方案 A：在 `app/api/v1/router.py` 中同时注册无版本别名：
```python
# 兼容旧路径（过渡期使用）
api_router.include_router(health.router, prefix="", deprecated=True)
```

方案 B：在 `nginx` 层做路径重写（生产环境推荐）。

方案 C：前端统一更新 API base URL。

---

## 十一、验收清单

完成迁移后，逐项确认：

**功能验收**
- [ ] `GET /api/v1/health` 返回 `status: ok` 和 vectorStore 统计
- [ ] `GET /api/v1/documents` 返回文档列表
- [ ] `GET /api/v1/audit` 返回最近审计日志
- [ ] `POST /api/v1/ingest/text` 文本入库成功，返回 201
- [ ] `POST /api/v1/ingest/text` 角色无权限时返回 403
- [ ] `POST /api/v1/ingest/text` 缺少必填字段时返回 422
- [ ] `POST /api/v1/ingest/file` 文件上传入库成功，返回 201
- [ ] `POST /api/v1/search` 语义检索返回结果和 rerank 信息
- [ ] `POST /api/v1/ask` RAG 问答返回 answer、sources、traceId
- [ ] 前端静态文件正常加载

**可观测性验收**
- [ ] 每个请求日志包含 `method`、`path`、`status_code`、`duration_ms`、`request_id`
- [ ] 响应 Header 中有 `X-Request-ID`
- [ ] 错误响应格式统一：`{"error": "...", "message": "...", "path": "..."}`
- [ ] 审计日志写入 `data/audit_log.jsonl`（包括 ingest、search、ask）

**文档验收**
- [ ] 访问 `http://host/api/docs` 能看到完整 OpenAPI 交互文档
- [ ] 所有接口都有 `summary` 描述
- [ ] 生产环境（`APP_ENV=prod`）下 `/api/docs` 不可访问

**测试验收**
- [ ] `pytest tests/ -v` 全部通过
- [ ] 覆盖：正常流程、权限拒绝、参数校验失败三类场景

---

## 十二、注意事项与已知坑

1. **`python-multipart` 必须安装**，否则 `UploadFile` + `Form` 会报 `422 Unprocessable Entity`，且错误信息不直观。

2. **StaticFiles 必须最后挂载**，`app.mount("/", ...)` 放在 `include_router` 之后，否则 `/api/*` 请求会被 StaticFiles 拦截返回 404。

3. **`pydantic-settings` 的 `.env` 路径用绝对路径**，`env_file=".env"` 在不同 `cwd` 启动时会找不到文件，应使用 `PROJECT_ROOT / ".env"`。

4. **同步 `def` 路由 vs `async def`**：FastAPI 对普通 `def` 路由会自动放入线程池执行，SQLite 同步操作完全兼容，不要为了"看起来现代"而强行加 `async`——那样反而需要处理 `run_in_threadpool`。

5. **Pydantic v2 的 `model_dump(by_alias=False)`**：向 services 传参时用 `by_alias=False`，保证字段名是 Python 风格（`blocked_count`），而非 JSON 别名（`blockedCount`）。

6. **`BackgroundTasks` 是进程内线程**，不是消息队列，应用重启时未执行的任务会丢失。生产环境如需可靠审计，后续可改为 Celery 或数据库写入。

7. **`APP_ENV=prod` 时关闭 OpenAPI 文档**（已在 `main.py` 中处理），防止接口信息泄露。

8. **CORS `allow_origins=["*"]` 在生产环境应收紧**，改为实际前端域名列表，在 `.env` 中配置 `CORS_ORIGINS=https://your-domain.com`。

