"""
健康检查路由 — v2
"""
from fastapi import APIRouter

from app.api.deps import AuditStoreDep
from app.core.config import settings
from app.services.platform_services.database import DatabaseReadinessService

router = APIRouter(tags=["健康检查"])


@router.get("/health", summary="服务健康检查")
async def health_check():
    db = await DatabaseReadinessService().check()
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "chroma_collection": settings.chroma_collection_v2,
        "database": db,
    }


@router.get("/audit", summary="最近审计日志")
def get_audit_log(audit: AuditStoreDep, limit: int = 50):
    return {"items": audit.recent(limit=limit)}
