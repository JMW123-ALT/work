"""
入库路由
- POST /ingest/text  — JSON 文本入库
- POST /ingest/file  — multipart 文件入库（支持多文件）
- POST /ingest       — 旧路径兼容（透传 /ingest/text 或 /ingest/file）
"""
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status

from app.api.deps import AuditStoreDep, VectorStoreDep
from app.core.exceptions import PermissionDeniedError
from app.schemas.ingest import (
    IngestResponse,
    IngestTextRequest,
    PermissionLevel,
)
from app.services.permissions import can_assign_permission, can_ingest

router = APIRouter(tags=["入库管理"])


def _check_permission(
    ingest_role: str,
    permission_level: str,
    operator: str,
    title: str,
    audit: AuditStoreDep,
) -> None:
    """权限检查公共逻辑，失败则记录审计日志并抛出 PermissionDeniedError。"""
    if not can_ingest(ingest_role):
        audit.record(
            "ingest_denied",
            ingest_role,
            {"operator": operator, "reason": "role_cannot_upload", "title": title},
        )
        raise PermissionDeniedError("当前入库角色没有上传权限。")

    if not can_assign_permission(ingest_role, permission_level):
        audit.record(
            "ingest_denied",
            ingest_role,
            {
                "operator": operator,
                "reason": "permission_level_too_high",
                "permissionLevel": permission_level,
                "title": title,
            },
        )
        raise PermissionDeniedError("当前入库角色不能创建该权限级别的资料。")


# ── 文本入库（JSON）─────────────────────────────────────────────────

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
    _check_permission(req.ingest_role, req.permission_level, req.operator, req.title, audit)

    item = vs.add_document(req.model_dump())

    background_tasks.add_task(
        audit.record,
        "ingest",
        req.ingest_role,
        {
            "operator": req.operator,
            "sourceId": item["source_id"],
            "permissionLevel": item["permission_level"],
            "modality": item["modality"],
            "chunkCount": item["chunk_count"],
        },
    )
    return IngestResponse(item=item)


# ── 文件入库（multipart）─────────────────────────────────────────────

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
    files: Annotated[list[UploadFile], File()],
    ingest_role: Annotated[str, Form()] = "none",
    operator: Annotated[str, Form()] = "local-admin",
    permission_level: Annotated[PermissionLevel, Form()] = "public",
    title: Annotated[str | None, Form()] = None,
    object_type: Annotated[str, Form()] = "internal_doc",
    access_channel: Annotated[str, Form()] = "web",
    source_id: Annotated[str | None, Form()] = None,
    content: Annotated[str | None, Form()] = None,
    modality: Annotated[str | None, Form()] = None,
):
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="至少需要上传一个文件。",
        )

    _check_permission(ingest_role, permission_level, operator, title or "", audit)

    fields = {
        "ingest_role": ingest_role,
        "operator": operator,
        "permission_level": permission_level,
        "title": title,
        "object_type": object_type,
        "access_channel": access_channel,
        "source_id": source_id,
        "content": content,
        "modality": modality,
    }

    items = []
    for upload in files:
        file_data = upload.file.read()
        file_item = {
            "field": "file",
            "filename": upload.filename or "unnamed",
            "content_type": upload.content_type or "",
            "data": file_data,
        }
        item = vs.add_file_document(fields, file_item)
        items.append(item)
        background_tasks.add_task(
            audit.record,
            "ingest_file",
            ingest_role,
            {
                "operator": operator,
                "sourceId": item["source_id"],
                "permissionLevel": item["permission_level"],
                "modality": item["modality"],
                "fileName": item["file_name"],
                "chunkCount": item["chunk_count"],
            },
        )

    return IngestResponse(items=items, item=items[0] if items else None)


# ── 旧路径兼容：/ingest（前端 app.js 使用此路径）──────────────────────

@router.post(
    "/ingest",
    status_code=status.HTTP_201_CREATED,
    summary="入库（兼容旧前端路径）",
    include_in_schema=False,
)
def ingest_compat(
    vs: VectorStoreDep,
    audit: AuditStoreDep,
    background_tasks: BackgroundTasks,
    # 文件字段（可选）
    files: Annotated[list[UploadFile] | None, File()] = None,
    # Form 字段（文件上传时由 multipart 传入）
    ingest_role: Annotated[str | None, Form()] = None,
    operator: Annotated[str | None, Form()] = None,
    permission_level: Annotated[str | None, Form()] = None,
    title: Annotated[str | None, Form()] = None,
    content: Annotated[str | None, Form()] = None,
    object_type: Annotated[str | None, Form()] = None,
    access_channel: Annotated[str | None, Form()] = None,
    source_id: Annotated[str | None, Form()] = None,
    modality: Annotated[str | None, Form()] = None,
):
    """兼容原前端发往 /api/ingest 的请求，根据是否携带文件分发到对应处理逻辑。"""
    _ingest_role = ingest_role or "none"
    _operator = operator or "local-admin"
    _permission_level = permission_level or "public"

    if files:
        _check_permission(_ingest_role, _permission_level, _operator, title or "", audit)
        fields = {
            "ingest_role": _ingest_role,
            "operator": _operator,
            "permission_level": _permission_level,
            "title": title,
            "object_type": object_type or "internal_doc",
            "access_channel": access_channel or "web",
            "source_id": source_id,
            "content": content,
            "modality": modality,
        }
        items = []
        for upload in files:
            file_data = upload.file.read()
            file_item = {
                "field": "file",
                "filename": upload.filename or "unnamed",
                "content_type": upload.content_type or "",
                "data": file_data,
            }
            item = vs.add_file_document(fields, file_item)
            items.append(item)
            background_tasks.add_task(
                audit.record,
                "ingest_file",
                _ingest_role,
                {
                    "operator": _operator,
                    "sourceId": item["source_id"],
                    "permissionLevel": item["permission_level"],
                    "modality": item["modality"],
                    "fileName": item["file_name"],
                    "chunkCount": item["chunk_count"],
                },
            )
        return {"items": items, "item": items[0] if items else None}

    # JSON 入库（无文件）
    if not title or not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="title and content are required",
        )
    _check_permission(_ingest_role, _permission_level, _operator, title, audit)
    payload = {
        "title": title,
        "content": content,
        "object_type": object_type or "internal_doc",
        "permission_level": _permission_level,
        "access_channel": access_channel or "web",
        "ingest_role": _ingest_role,
        "operator": _operator,
        "modality": modality or "text",
    }
    item = vs.add_document(payload)
    background_tasks.add_task(
        audit.record,
        "ingest",
        _ingest_role,
        {
            "operator": _operator,
            "sourceId": item["source_id"],
            "permissionLevel": item["permission_level"],
            "modality": item["modality"],
            "chunkCount": item["chunk_count"],
        },
    )
    return {"item": item}
