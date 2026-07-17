"""
文档管理路由 — v2 PostgreSQL
- GET  /documents              — 列表
- GET  /documents/{id}         — 单文档状态
- GET  /documents/{id}/file    — 下载/查看原始上传文件
- DELETE /documents/{id}       — 删除
- POST /documents/{id}/retry   — 重试失败索引
"""
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select

from app.core.config import settings
from app.core.logging import logger
from app.db.models.documents import Chunk, Document, DocumentFile, DocumentVersion
from app.db.session import async_session_factory

router = APIRouter(tags=["文档管理"])


def _require_session():
    if async_session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DATABASE_URL 未配置",
        )


def _doc_to_dict(doc: Document, chunk_count: int = 0, file_name: str = "", file_size: int = 0, content: str = "") -> dict:
    return {
        "source_id": doc.id,
        "document_id": doc.id,
        "title": doc.title,
        "modality": doc.modality,
        "permission_level": doc.permission_level,
        "status": doc.status,
        "error_message": doc.error_message if doc.error_message else None,
        "object_type": doc.object_type,
        "access_channel": doc.access_channel,
        "original_ref_uri": doc.original_ref_uri,
        "file_sha256": doc.file_sha256,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
        "chunk_count": chunk_count,
        "extraction_status": doc.status,
        "file_name": file_name,
        "file_size": file_size,
        "content": content,   # 正文文本，供 BrowsePage 摘要和详情展示
    }


@router.get("/documents", summary="获取所有文档列表")
async def list_documents():
    _require_session()
    org_id = settings.default_organization_id
    async with async_session_factory() as session:
        result = await session.execute(
            select(Document)
            .where(Document.organization_id == org_id, Document.status != "deleted")
            .order_by(Document.created_at.desc())
        )
        docs = result.scalars().all()
        doc_ids = [d.id for d in docs]

        # Chunk counts
        chunk_counts = {}
        if doc_ids:
            cc = await session.execute(
                select(Chunk.document_id, func.count(Chunk.id).label("cnt"))
                .where(Chunk.document_id.in_(doc_ids))
                .group_by(Chunk.document_id)
            )
            chunk_counts = {r.document_id: r.cnt for r in cc}

        # File info
        file_info = {}
        if doc_ids:
            fr = await session.execute(
                select(DocumentFile.document_id, DocumentFile.file_name, DocumentFile.file_size)
                .where(DocumentFile.document_id.in_(doc_ids))
            )
            for row in fr:
                if row.document_id not in file_info:
                    file_info[row.document_id] = (row.file_name, row.file_size)

        # 正文内容：从最新 DocumentVersion 获取
        content_map = {}
        if doc_ids:
            vr = await session.execute(
                select(DocumentVersion.document_id, DocumentVersion.content)
                .where(DocumentVersion.document_id.in_(doc_ids))
                .order_by(DocumentVersion.document_id, DocumentVersion.version.desc())
            )
            for row in vr:
                if row.document_id not in content_map:
                    content_map[row.document_id] = row.content

    items = [
        _doc_to_dict(
            d,
            chunk_count=chunk_counts.get(d.id, 0),
            file_name=file_info.get(d.id, ("", 0))[0],
            file_size=file_info.get(d.id, ("", 0))[1],
            content=content_map.get(d.id, ""),
        )
        for d in docs
    ]
    return {"items": items}


@router.get("/documents/{document_id}", summary="获取单个文档状态")
async def get_document(document_id: str):
    _require_session()
    async with async_session_factory() as session:
        doc = await session.get(Document, document_id)
        if doc is None or doc.status == "deleted":
            raise HTTPException(status_code=404, detail="文档不存在")
        cnt = (await session.execute(
            select(func.count(Chunk.id)).where(Chunk.document_id == doc.id)
        )).scalar_one()
        file_row = (await session.execute(
            select(DocumentFile.file_name, DocumentFile.file_size)
            .where(DocumentFile.document_id == doc.id).limit(1)
        )).fetchone()
        ver_row = (await session.execute(
            select(DocumentVersion.content)
            .where(DocumentVersion.document_id == doc.id)
            .order_by(DocumentVersion.version.desc()).limit(1)
        )).fetchone()
    return _doc_to_dict(
        doc,
        chunk_count=cnt,
        file_name=file_row[0] if file_row else "",
        file_size=file_row[1] if file_row else 0,
        content=ver_row[0] if ver_row else "",
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除文档")
async def delete_document(document_id: str):
    _require_session()
    async with async_session_factory() as session:
        doc = await session.get(Document, document_id)
        if doc is None or doc.status == "deleted":
            raise HTTPException(status_code=404, detail="文档不存在")
        if doc.status == "deleting":
            return  # already in progress

        # 1. Immediately mark deleting → excluded from retrieval
        doc.status = "deleting"
        doc.updated_at = datetime.now(timezone.utc)
        await session.commit()

    # 2. Delete Chroma vectors
    _delete_chroma_vectors(document_id)

    # 3. Delete managed upload file
    async with async_session_factory() as session:
        doc = await session.get(Document, document_id)
        if doc:
            _delete_managed_file(doc.original_ref_uri)
            # 4. Delete PostgreSQL rows (cascade deletes chunks/versions/files)
            await session.delete(doc)
            await session.commit()


@router.post("/documents/{document_id}/retry", summary="重试失败的索引任务")
async def retry_document(document_id: str):
    _require_session()
    from fastapi import BackgroundTasks
    from app.services.platform_services.indexing import index_document_background

    async with async_session_factory() as session:
        doc = await session.get(Document, document_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="文档不存在")
        if doc.status not in ("failed", "queued"):
            raise HTTPException(
                status_code=400,
                detail=f"只有 failed 或 queued 状态的文档才能重试，当前状态: {doc.status}",
            )
        doc.status = "queued"
        doc.error_message = ""
        doc.updated_at = datetime.now(timezone.utc)

        # Delete existing chunks to allow fresh indexing
        existing_chunks = await session.execute(
            select(Chunk).where(Chunk.document_id == doc.id)
        )
        for chunk in existing_chunks.scalars().all():
            await session.delete(chunk)

        await session.commit()

    # Schedule re-indexing (use a new BackgroundTasks — fire-and-forget via asyncio)
    import asyncio
    asyncio.create_task(index_document_background(document_id))

    return {"document_id": document_id, "status": "queued", "message": "已重新排队"}


# MIME type map for common file extensions
_MIME_MAP = {
    ".pdf":  "application/pdf",
    ".doc":  "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls":  "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".ppt":  "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".gif":  "image/gif",
    ".webp": "image/webp",
    ".txt":  "text/plain; charset=utf-8",
    ".md":   "text/plain; charset=utf-8",
}


@router.get("/documents/{document_id}/file", summary="查看/下载原始上传文件")
async def get_document_file(document_id: str, download: bool = False):
    """Serve the original uploaded file.

    PDF / image files are served inline (browser can render them).
    Office/PPT/Word files are served as attachment (download).
    Pass ?download=true to force download for any type.
    """
    _require_session()
    async with async_session_factory() as session:
        doc = await session.get(Document, document_id)
    if doc is None or doc.status == "deleted":
        raise HTTPException(status_code=404, detail="文档不存在")

    uri = doc.original_ref_uri or ""
    if not uri.startswith("upload://"):
        raise HTTPException(status_code=404, detail="该文档没有原始上传文件")

    stored_name = uri[len("upload://"):]
    upload_root = settings.upload_dir.resolve()
    file_path = (settings.upload_dir / stored_name).resolve()

    # Safety: only serve files inside managed upload_dir
    if not str(file_path).startswith(str(upload_root)):
        raise HTTPException(status_code=403, detail="非法路径")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在（可能已被清理）")

    suffix = file_path.suffix.lower()
    media_type = _MIME_MAP.get(suffix, "application/octet-stream")

    # Inline for PDF and images; attachment (download) for Office files
    inline_types = {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".txt", ".md"}
    disposition = "attachment" if (download or suffix not in inline_types) else "inline"

    # Use the original filename for the Content-Disposition header.
    # stored_name = "{source_id}-{safe_original_name}", strip the source_id prefix.
    parts = stored_name.split("-", 2)
    display_name = parts[-1] if len(parts) >= 2 else stored_name

    # RFC 5987 encoding: supports Unicode filenames in HTTP headers.
    # filename*=UTF-8''<percent-encoded> takes priority over filename= in modern browsers.
    from urllib.parse import quote
    encoded_name = quote(display_name, safe="")
    ascii_fallback = display_name.encode("ascii", errors="replace").decode("ascii")
    content_disposition = (
        f'{disposition}; filename="{ascii_fallback}"; '
        f"filename*=UTF-8''{encoded_name}"
    )

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        headers={
            "Content-Disposition": content_disposition,
            "Cache-Control": "private, max-age=3600",
        },
    )


def _delete_chroma_vectors(document_id: str) -> None:
    """Idempotent: delete all Chroma vectors for a document."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(settings.chroma_path))
        collection = client.get_or_create_collection(
            name=settings.chroma_collection_v2,
        )
        # Chroma metadata filter: delete all chunks belonging to this document
        # Get all chunk IDs first (Chroma doesn't support delete-by-metadata directly in all versions)
        results = collection.get(
            where={"document_id": {"$eq": document_id}},
            include=[],  # only IDs needed
        )
        ids_to_delete = results.get("ids") or []
        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            logger.info("Deleted %d Chroma vectors for document %s", len(ids_to_delete), document_id)
    except Exception as exc:
        logger.warning("Could not delete Chroma vectors for %s: %s", document_id, exc)


def _delete_managed_file(original_ref_uri: str) -> None:
    """Delete the uploaded file only if it is inside the managed upload_dir."""
    if not original_ref_uri or not original_ref_uri.startswith("upload://"):
        return
    stored_name = original_ref_uri[len("upload://"):]
    upload_root = settings.upload_dir.resolve()
    target = (settings.upload_dir / stored_name).resolve()
    # Safety: only delete files under the managed root
    if not str(target).startswith(str(upload_root)):
        logger.error("Refusing to delete file outside upload_root: %s", target)
        return
    try:
        if target.exists():
            target.unlink()
            logger.info("Deleted managed file: %s", target)
    except Exception as exc:
        logger.warning("Could not delete managed file %s: %s", target, exc)
