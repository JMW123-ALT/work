"""
HTTP 访问日志中间件：记录请求耗时、状态码
"""
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import logger

# 健康检查路径不记录，避免日志噪音
_SKIP_PATHS = {"/api/v1/health"}


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "HTTP %s %s → %s  %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "request_id": getattr(request.state, "request_id", "-"),
                "client_ip": request.client.host if request.client else "-",
            },
        )
        return response
