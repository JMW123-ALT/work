"""
FastAPI 依赖注入：将 services 单例封装为可注入依赖，便于测试时替换
"""
from typing import Annotated

from fastapi import Depends, Header

from app.services.audit import AuditStore, audit_store
from app.services.permissions import normalize_ingest_role, normalize_user_type
from app.services.rag_service import RAGService, rag_service
from app.services.vector_store import VectorStore, vector_store


# ── 服务层依赖 ────────────────────────────────────────────────────

def get_vector_store() -> VectorStore:
    return vector_store


def get_rag_service() -> RAGService:
    return rag_service


def get_audit_store() -> AuditStore:
    return audit_store


VectorStoreDep = Annotated[VectorStore, Depends(get_vector_store)]
RAGServiceDep = Annotated[RAGService, Depends(get_rag_service)]
AuditStoreDep = Annotated[AuditStore, Depends(get_audit_store)]


# ── 认证依赖（当前基于 Header 角色，预留 JWT 扩展） ─────────────────

def get_user_type(
    x_user_type: Annotated[str | None, Header(alias="X-User-Type")] = None,
) -> str:
    """从 X-User-Type Header 获取用户类型；未来可替换为 JWT 解析。"""
    return normalize_user_type(x_user_type or "visitor")


def get_ingest_role(
    x_ingest_role: Annotated[str | None, Header(alias="X-Ingest-Role")] = None,
) -> str:
    """从 X-Ingest-Role Header 获取入库角色；未来可替换为 JWT claims。"""
    return normalize_ingest_role(x_ingest_role or "none")


UserTypeDep = Annotated[str, Depends(get_user_type)]
IngestRoleDep = Annotated[str, Depends(get_ingest_role)]
