"""
FastAPI 应用工厂
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
    """应用生命周期：启动 / 关闭时记录日志"""
    logger.info(
        "Application starting — env=%s  host=%s  port=%s",
        settings.app_env,
        settings.app_host,
        settings.app_port,
    )
    yield
    logger.info("Application shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="旅游知识向量数据库 API（FastAPI 版）",
        docs_url="/api/docs" if settings.app_env != "prod" else None,
        redoc_url="/api/redoc" if settings.app_env != "prod" else None,
        openapi_url="/api/openapi.json" if settings.app_env != "prod" else None,
        lifespan=lifespan,
    )

    # ── 中间件（后注册先执行，顺序：RequestID → AccessLog → CORS） ───────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # ── 全局异常处理器 ────────────────────────────────────────────────
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    # ── API 路由（/api/v1/*）── 必须在静态文件之前注册 ─────────────────
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    # ── 旧路径兼容别名（/api/health、/api/documents 等）──────────────
    # 前端 app.js 使用不带 /v1 的路径，在这里挂一个兼容前缀
    app.include_router(api_router, prefix="/api", include_in_schema=False)

    # ── 静态前端文件（最后挂载，避免吃掉 /api/* 路径）──────────────────
    frontend_dir = settings.data_dir.parents[1] / "frontend"
    if frontend_dir.exists():
        app.mount(
            "/",
            StaticFiles(directory=str(frontend_dir), html=True),
            name="frontend",
        )

    return app


# 全局应用实例（供 uvicorn 使用）
app = create_app()
