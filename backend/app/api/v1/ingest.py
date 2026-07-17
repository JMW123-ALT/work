"""
入库路由 — v2 PostgreSQL + BackgroundTasks
- POST /ingest/text  — JSON 文本入库
- POST /ingest/file  — multipart 文件入库（支持多文件）
- POST /ingest       — 旧路径兼容

v1 SQLite/VectorStore 路径已弃用，所有入库现在写 PostgreSQL v2。
前端不传 organization_id；后端自动注入 settings.default_organization_id。
"""
import hashlib
import re
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import logger
from app.db.models.documents import Document
from app.db.session import async_session_factory
from app.api.deps import AuditStoreDep
from app.core.exceptions import PermissionDeniedError
from app.schemas.ingest import IngestTextRequest, PermissionLevel
from app.services.permissions import can_assign_permission, can_ingest
from app.services.platform_services.indexing import index_document_background

router = APIRouter(tags=["入库管理"])


def _check_permission(
    ingest_role: str,
    permission_level: str,
    operator: str,
    title: str,
    audit: AuditStoreDep,
) -> None:
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


def _require_session():
    if async_session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DATABASE_URL 未配置，请设置 PostgreSQL 连接后重启。",
        )


# ── 文本入库（JSON）─────────────────────────────────────────────────────────

@router.post(
    "/ingest/text",
    status_code=status.HTTP_201_CREATED,
    summary="文本内容入库（JSON）",
)
async def ingest_text(
    req: IngestTextRequest,
    audit: AuditStoreDep,
    background_tasks: BackgroundTasks,
):
    _require_session()
    _check_permission(req.ingest_role, req.permission_level, req.operator, req.title, audit)

    org_id = settings.default_organization_id
    content_sha256 = hashlib.sha256(req.content.encode()).hexdigest()

    async with async_session_factory() as session:
        # Dedup: same org + same content hash
        existing = await session.execute(
            select(Document).where(
                Document.organization_id == org_id,
                Document.content_sha256 == content_sha256,
                Document.status != "deleted",
            )
        )
        existing_doc = existing.scalar_one_or_none()
        if existing_doc:
            return _ingest_response(existing_doc, duplicate=True)

        doc = Document(
            organization_id=org_id,
            source_id=f"src-text-{content_sha256[:12]}",
            title=req.title,
            object_type=req.object_type,
            permission_level=req.permission_level,
            access_channel=req.access_channel,
            original_ref_uri=req.original_ref_uri or "manual://text-entry",
            modality=req.modality,
            content_sha256=content_sha256,
            status="queued",
        )
        session.add(doc)
        await session.flush()
        doc_id = doc.id
        # Store content in metadata for the indexing service to use
        doc.original_ref_uri = f"text://{content_sha256}"
        await session.commit()

    # Write content to a temp file so the indexing service can pick it up
    text_dir = settings.upload_dir / "_text"
    text_dir.mkdir(parents=True, exist_ok=True)
    text_file = text_dir / f"{doc_id}.txt"
    text_file.write_text(req.content, encoding="utf-8")

    # Update original_ref_uri to point to the text file
    async with async_session_factory() as session:
        d = await session.get(Document, doc_id)
        if d:
            d.original_ref_uri = f"upload://_text/{doc_id}.txt"
            await session.commit()

    background_tasks.add_task(index_document_background, doc_id)
    background_tasks.add_task(
        audit.record,
        "ingest",
        req.ingest_role,
        {"operator": req.operator, "documentId": doc_id, "permissionLevel": req.permission_level},
    )

    # Return a minimal response compatible with the old IngestResponse shape
    return {
        "item": {
            "source_id": doc_id,
            "document_id": doc_id,
            "title": req.title,
            "modality": req.modality,
            "permission_level": req.permission_level,
            "status": "queued",
            "chunk_count": 0,
            "extraction_status": "queued",
        },
        "items": [],
    }


# ── 文件入库（multipart）─────────────────────────────────────────────────────

@router.post(
    "/ingest/file",
    status_code=status.HTTP_201_CREATED,
    summary="文件入库（multipart/form-data，支持 PDF/图片/Office）",
)
async def ingest_file(
    audit: AuditStoreDep,
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile], File()],
    ingest_role: Annotated[str, Form()] = "none",
    operator: Annotated[str, Form()] = "local-admin",
    permission_level: Annotated[PermissionLevel, Form()] = "internal",
    title: Annotated[str | None, Form()] = None,
    object_type: Annotated[str, Form()] = "internal_doc",
    access_channel: Annotated[str, Form()] = "web_upload",
    source_id: Annotated[str | None, Form()] = None,
    content: Annotated[str | None, Form()] = None,
    modality: Annotated[str | None, Form()] = None,
):
    _require_session()
    if not files:
        raise HTTPException(status_code=400, detail="至少需要上传一个文件。")

    _check_permission(ingest_role, permission_level, operator, title or "", audit)

    org_id = settings.default_organization_id
    results = []

    for upload in files:
        file_bytes = await upload.read()
        result = await _process_one_upload(
            file_bytes=file_bytes,
            file_name=upload.filename or "unnamed",
            mime_type=upload.content_type or "",
            org_id=org_id,
            permission_level=permission_level,
            object_type=object_type,
            access_channel=access_channel,
            title=title,
            modality=modality,
            background_tasks=background_tasks,
        )
        results.append(result)
        background_tasks.add_task(
            audit.record,
            "ingest_file",
            ingest_role,
            {
                "operator": operator,
                "documentId": result["document_id"],
                "permissionLevel": permission_level,
                "fileName": upload.filename or "unnamed",
                "duplicate": result.get("duplicate", False),
            },
        )

    return {"items": results, "item": results[0] if results else None}


# ── 旧路径兼容 ────────────────────────────────────────────────────────────────

@router.post(
    "/ingest",
    status_code=status.HTTP_201_CREATED,
    summary="入库（兼容旧前端路径）",
    include_in_schema=False,
)
async def ingest_compat(
    audit: AuditStoreDep,
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile] | None, File()] = None,
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
    _ingest_role = ingest_role or "admin"
    _operator = operator or "local-admin"
    _permission_level = permission_level or "internal"

    if files:
        return await ingest_file(
            audit=audit,
            background_tasks=background_tasks,
            files=files,
            ingest_role=_ingest_role,
            operator=_operator,
            permission_level=_permission_level,
            title=title,
            object_type=object_type or "internal_doc",
            access_channel=access_channel or "web_upload",
            source_id=source_id,
            content=content,
            modality=modality,
        )

    if not title or not content:
        raise HTTPException(status_code=400, detail="title and content are required")

    from app.schemas.ingest import IngestTextRequest as _TextReq
    req = _TextReq(
        title=title,
        content=content,
        object_type=object_type or "internal_doc",
        permission_level=_permission_level,
        access_channel=access_channel or "web",
        ingest_role=_ingest_role,
        operator=_operator,
        modality=modality or "text",
    )
    return await ingest_text(req=req, audit=audit, background_tasks=background_tasks)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _process_one_upload(
    *,
    file_bytes: bytes,
    file_name: str,
    mime_type: str,
    org_id: str,
    permission_level: str,
    object_type: str,
    access_channel: str,
    title: str | None,
    modality: str | None,
    background_tasks: BackgroundTasks,
) -> dict:
    file_sha256 = hashlib.sha256(file_bytes).hexdigest()

    async with async_session_factory() as session:
        # SHA-256 dedup within same org
        existing = await session.execute(
            select(Document).where(
                Document.organization_id == org_id,
                Document.file_sha256 == file_sha256,
                Document.status != "deleted",
            )
        )
        existing_doc = existing.scalar_one_or_none()
        if existing_doc:
            return _ingest_response(existing_doc, duplicate=True)

        # Save file with managed name (never use raw client filename as path)
        safe_name = _safe_file_name(file_name)
        doc_source_id = source_id_for_sha(file_sha256)
        stored_name = f"{doc_source_id}-{safe_name}"
        upload_dir = settings.upload_dir
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Safety check: ensure stored path stays within upload_dir
        stored_path = (upload_dir / stored_name).resolve()
        if not str(stored_path).startswith(str(upload_dir.resolve())):
            raise HTTPException(status_code=400, detail="Invalid file name.")

        stored_path.write_bytes(file_bytes)

        detected_modality = modality or _detect_modality(file_name, mime_type)
        doc_title = (title or Path(file_name).stem or "Untitled").strip()

        doc = Document(
            organization_id=org_id,
            source_id=doc_source_id,
            title=doc_title,
            object_type=object_type,
            access_channel=access_channel,
            original_ref_uri=f"upload://{stored_name}",
            modality=detected_modality,
            file_sha256=file_sha256,
            permission_level=permission_level,
            status="queued",
        )
        session.add(doc)
        await session.flush()
        doc_id = doc.id
        await session.commit()

    background_tasks.add_task(index_document_background, doc_id)
    return {
        "document_id": doc_id,
        "source_id": doc_source_id,
        "title": doc_title,
        "modality": detected_modality,
        "permission_level": permission_level,
        "status": "queued",
        "file_name": file_name,
        "file_size": len(file_bytes),
        "chunk_count": 0,
        "extraction_status": "queued",
        "duplicate": False,
    }


def _ingest_response(doc: Document, duplicate: bool) -> dict:
    return {
        "document_id": doc.id,
        "source_id": doc.source_id,
        "title": doc.title,
        "modality": doc.modality,
        "permission_level": doc.permission_level,
        "status": doc.status,
        "chunk_count": 0,
        "extraction_status": doc.status,
        "duplicate": duplicate,
    }


def source_id_for_sha(file_sha256: str) -> str:
    return f"src-file-{file_sha256[:12]}"


def _safe_file_name(filename: str) -> str:
    name = Path(filename or "upload.bin").name
    clean = re.sub(r"[^0-9A-Za-z._\-一-鿿]+", "_", name)
    return (clean or "upload.bin")[:120]


def _detect_modality(file_name: str, mime_type: str) -> str:
    ext = Path(file_name).suffix.lower().lstrip(".")
    if ext == "pdf" or "pdf" in mime_type:
        return "pdf"
    if ext in ("doc", "docx", "xls", "xlsx", "ppt", "pptx") or "office" in mime_type:
        return "office"
    if ext in ("jpg", "jpeg", "png", "gif", "webp", "bmp") or mime_type.startswith("image/"):
        return "image"
    return "text"
