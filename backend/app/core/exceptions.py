"""
自定义异常类和全局异常处理器
"""
import traceback
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    """应用基础异常"""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(self.message)


class PermissionDeniedError(AppException):
    """权限不足"""

    def __init__(self, message: str = "权限不足", detail: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class ValidationError(AppException):
    """业务验证异常"""

    def __init__(self, message: str, detail: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class ResourceNotFoundError(AppException):
    """资源未找到"""

    def __init__(self, message: str = "资源不存在", detail: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND, detail=detail)


# ── 全局异常处理器 ─────────────────────────────────────────────────


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "detail": exc.detail, "path": str(request.url.path)},
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "validation_error",
            "message": str(exc),
            "path": str(request.url.path),
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": exc.detail,
            "path": str(request.url.path),
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    from app.core.logging import logger

    logger.error(
        "Unhandled exception",
        extra={
            "path": str(request.url.path),
            "method": request.method,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        },
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "服务器内部错误",
            "path": str(request.url.path),
        },
    )
