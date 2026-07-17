"""
FastAPI 依赖注入 — v2
v1 SQLite VectorStore 和 RAGService 依赖已移除。
"""
from typing import Annotated

from fastapi import Depends, Header

from app.services.audit import AuditStore, audit_store
from app.services.permissions import normalize_ingest_role, normalize_user_type


def get_audit_store() -> AuditStore:
    return audit_store


AuditStoreDep = Annotated[AuditStore, Depends(get_audit_store)]


def get_user_type(
    x_user_type: Annotated[str | None, Header(alias="X-User-Type")] = None,
) -> str:
    return normalize_user_type(x_user_type or "visitor")


def get_ingest_role(
    x_ingest_role: Annotated[str | None, Header(alias="X-Ingest-Role")] = None,
) -> str:
    return normalize_ingest_role(x_ingest_role or "none")


UserTypeDep = Annotated[str, Depends(get_user_type)]
IngestRoleDep = Annotated[str, Depends(get_ingest_role)]
