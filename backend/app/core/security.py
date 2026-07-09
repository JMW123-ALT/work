"""
认证/授权工具函数（预留 JWT 扩展位置）
当前版本基于 Header 角色，未接入真实认证。
"""
from fastapi import Header, HTTPException, status
from typing import Annotated


# 预留：future JWT 验证函数放在这里
# async def verify_token(token: str) -> dict: ...


def require_admin(x_ingest_role: Annotated[str | None, Header(alias="X-Ingest-Role")] = None) -> str:
    """示例：要求 admin 角色，否则 403。当前未使用，供路由层扩展。"""
    if (x_ingest_role or "").lower() != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要 admin 角色")
    return "admin"
