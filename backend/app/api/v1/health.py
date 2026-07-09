from fastapi import APIRouter

from app.api.deps import AuditStoreDep, VectorStoreDep
from app.core.config import settings

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
