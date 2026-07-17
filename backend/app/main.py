"""
FastAPI 应用工厂 — v2
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import HTTPException
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时恢复遗留索引任务，关闭时记录日志。"""
    logger.info(
        "Application starting — env=%s  host=%s  port=%s",
        settings.app_env,
        settings.app_host,
        settings.app_port,
    )

    # Recover stale indexing tasks left by a previous process restart.
    # Docs stuck in 'parsing' or 'embedding' are reset to 'failed' so users
    # can explicitly retry via POST /documents/{id}/retry.
    from app.services.platform_services.indexing import recover_stale_documents
    recovered = await recover_stale_documents()
    if recovered:
        logger.warning("Startup: reset %d stale indexing task(s) to 'failed'", recovered)

    yield
    logger.info("Application shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="2.0.0",
        description="文旅文创知识库与文创 Agent API — v2 (PostgreSQL + Chroma v2 + BackgroundTasks)",
        docs_url="/api/docs" if settings.app_env != "prod" else None,
        redoc_url="/api/redoc" if settings.app_env != "prod" else None,
        openapi_url="/api/openapi.json" if settings.app_env != "prod" else None,
        lifespan=lifespan,
    )

    # ── 中间件 ─────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # ── 全局异常处理器 ──────────────────────────────────────────────────────
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    # ── API 路由 ────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    # ── 旧路径兼容别名 (/api/health, /api/documents 等) ─────────────────────
    app.include_router(api_router, prefix="/api", include_in_schema=False)

    # ── 静态前端文件 ────────────────────────────────────────────────────────
    # 只挂载构建产物（dist/），不挂载源码目录（frontend/）。
    # 挂载 StaticFiles("/",...) 会拦截所有 POST 请求并返回 405，
    # 因为 StaticFiles 只支持 GET/HEAD。
    # 开发时通过 Vite dev server（port 5173）访问前端，无需此挂载。
    dist_dir = settings.data_dir.parents[1] / "dist"
    if dist_dir.exists():
        app.mount(
            "/",
            StaticFiles(directory=str(dist_dir), html=True),
            name="frontend",
        )

    return app


app = create_app()
