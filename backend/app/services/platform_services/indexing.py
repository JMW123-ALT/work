"""BackgroundTasks document indexing service.

Pipeline: queued → parsing → embedding → ready (or failed).

Handles two scenarios:
  1. Fresh document  — no DocumentVersion yet: full parse + chunk + embed
  2. Retry/re-index  — DocumentVersion + Chunks already exist, Chroma was reset:
                       skip parsing, only re-embed pending chunks

Key design rule: the executor receives only plain Python values (str, Path, …),
never SQLAlchemy ORM objects. This avoids greenlet_spawn errors that occur when
asyncpg is called from a synchronous thread context.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.db.models.documents import Chunk, Document, DocumentVersion
from app.db.session import async_session_factory
from app.services.chunking_client import chunking_client
from app.services.embedding_client import embedding_client
from app.services.platform_services.retrieval import _to_chroma_embedding


# ── Public entry points ───────────────────────────────────────────────────────

async def index_document_background(document_id: str) -> None:
    """Entry point for FastAPI BackgroundTasks."""
    if async_session_factory is None:
        logger.error("index_document_background: DATABASE_URL not configured, skipping %s", document_id)
        return
    try:
        await _run_indexing(document_id)
    except Exception as exc:
        logger.exception("index_document_background: unhandled error for %s: %s", document_id, exc)


async def recover_stale_documents() -> int:
    """Reset docs stuck in 'parsing'/'embedding' to 'failed' at startup."""
    if async_session_factory is None:
        return 0
    async with async_session_factory() as session:
        result = await session.execute(
            update(Document)
            .where(Document.status.in_(["parsing", "embedding"]))
            .values(
                status="failed",
                error_message="Process restarted during indexing. Use retry to re-index.",
                updated_at=datetime.now(timezone.utc),
            )
            .returning(Document.id)
        )
        recovered = list(result.scalars().all())
        await session.commit()
    if recovered:
        logger.warning("recover_stale_documents: reset %d stale document(s) to 'failed'", len(recovered))
    return len(recovered)


# ── Core pipeline ─────────────────────────────────────────────────────────────

async def _run_indexing(document_id: str) -> None:
    """Full indexing pipeline.  Two branches:
      • Fresh:  no version yet   → parse → write version+chunks → embed → ready
      • Retry:  version exists   → skip parse, re-embed pending chunks → ready
    """
    async with async_session_factory() as session:
        doc = await session.get(Document, document_id)
        if doc is None:
            logger.warning("_run_indexing: document %s not found", document_id)
            return
        if doc.status not in ("queued",):
            logger.info("_run_indexing: %s status=%s, skipping", document_id, doc.status)
            return

        # Check existing state
        existing_ver = (await session.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == doc.id)
            .order_by(DocumentVersion.version.desc())
            .limit(1)
        )).scalar_one_or_none()

        pending_chunks = list((await session.execute(
            select(Chunk)
            .where(Chunk.document_id == doc.id, Chunk.vector_status.in_(["pending", "failed"]))
            .order_by(Chunk.chunk_index)
        )).scalars().all())

        # --- Branch A: retry (version + chunks exist, Chroma was reset) ---
        if existing_ver is not None and pending_chunks:
            logger.info("_run_indexing: retry path for %s — %d chunks to embed", document_id[:8], len(pending_chunks))
            doc.status = "embedding"
            doc.updated_at = datetime.now(timezone.utc)
            chunk_ids = [c.id for c in pending_chunks]
            await session.commit()

        # --- Branch B: fresh document (no version yet, or no pending chunks) ---
        elif existing_ver is None:
            # Extract plain values before entering executor
            plain = _doc_plain(doc)
            doc.status = "parsing"
            doc.updated_at = datetime.now(timezone.utc)
            await session.commit()

            try:
                ver_data, raw_chunks = await asyncio.get_event_loop().run_in_executor(
                    None, _parse_and_chunk_plain,
                    plain["id"], plain["source_id"], plain["title"],
                    plain["modality"], plain["original_ref_uri"],
                )
            except Exception as exc:
                await _set_failed_new_session(document_id, f"Parsing failed: {exc!s}")
                return

            # Write version + chunks inside a fresh session
            try:
                async with async_session_factory() as s2:
                    d2 = await s2.get(Document, document_id)
                    if d2 is None or d2.status in ("deleting", "deleted"):
                        return

                    doc_ver = DocumentVersion(
                        document_id=document_id,
                        version=1,
                        title=plain["title"],
                        content=ver_data["content"],
                        content_sha256=ver_data["content_sha256"],
                        parser="chunking_client",
                        extraction_status=ver_data["extraction_status"],
                        metadata_json={},
                    )
                    s2.add(doc_ver)
                    await s2.flush()

                    for c in raw_chunks:
                        s2.add(Chunk(
                            document_id=document_id,
                            document_version_id=doc_ver.id,
                            chunk_id=c["chunk_id"],
                            source_id=plain["source_id"],
                            chunk_index=int(c["chunk_index"]),
                            section_path=c.get("section_path", plain["title"]),
                            content=c["content"],
                            modality=c.get("modality", plain["modality"]),
                            parser=c.get("parser", ""),
                            page_number=int(c.get("page_number") or 0),
                            asset_path=c.get("asset_path", ""),
                            asset_mime_type=c.get("asset_mime_type", ""),
                            embedding_modality=c.get("embedding_modality", "text"),
                            content_hash=_hash(c["content"]),
                            token_count=len(c["content"]),
                            vector_status="pending",
                        ))

                    d2.status = "embedding"
                    d2.updated_at = datetime.now(timezone.utc)
                    await s2.commit()

                # Collect chunk IDs for embedding
                async with async_session_factory() as s3:
                    rows = (await s3.execute(
                        select(Chunk.id).where(
                            Chunk.document_id == document_id,
                            Chunk.vector_status == "pending",
                        )
                    )).scalars().all()
                    chunk_ids = list(rows)

            except Exception as exc:
                await _set_failed_new_session(document_id, f"DB write failed: {exc!s}")
                return

        else:
            # version exists but no pending chunks → already ready
            async with async_session_factory() as s:
                d = await s.get(Document, document_id)
                if d:
                    d.status = "ready"
                    d.updated_at = datetime.now(timezone.utc)
                    await s.commit()
            return

    # --- Embedding stage (both branches converge here) ---
    await _embed_chunks(document_id, chunk_ids)


async def _embed_chunks(document_id: str, chunk_ids: list[str]) -> None:
    """Embed and upsert chunks into Chroma v2.  Uses a fresh session per batch."""
    if not chunk_ids:
        await _set_ready_new_session(document_id)
        return

    async with async_session_factory() as session:
        doc = await session.get(Document, document_id)
        if doc is None or doc.status in ("deleting", "deleted"):
            return

        # Load all chunks + doc info we need
        chunks_res = await session.execute(
            select(Chunk).where(Chunk.id.in_(chunk_ids)).order_by(Chunk.chunk_index)
        )
        chunks = list(chunks_res.scalars().all())

        # Snapshot plain values for the executor
        doc_permission = doc.permission_level
        doc_org_id = doc.organization_id
        chunks_plain = [
            {
                "id": c.id,
                "content": c.content,
                "chunk_index": c.chunk_index,
                "section_path": c.section_path,
                "modality": c.modality,
                "page_number": c.page_number,
            }
            for c in chunks
        ]

    collection = _get_chroma_collection()
    indexed, failed = 0, 0

    for cp in chunks_plain:
        # Guard: stop if document was deleted mid-run
        async with async_session_factory() as gs:
            live = await gs.get(Document, document_id)
            if live is None or live.status in ("deleting", "deleted"):
                logger.info("_embed_chunks: %s deleted mid-run", document_id[:8])
                return

        try:
            vector = await asyncio.get_event_loop().run_in_executor(
                None, embedding_client.embed_text, cp["content"]
            )
            chroma_vec = _to_chroma_embedding(vector)
            meta = {
                "chunk_id": cp["id"],
                "document_id": document_id,
                "organization_id": doc_org_id,
                "permission_level": doc_permission,
                "chunk_index": int(cp["chunk_index"]),
                "section_path": cp["section_path"] or "",
                "modality": cp["modality"] or "text",
                "page_number": int(cp["page_number"] or 0),
                "embedding_version": "v2",
            }
            collection.upsert(
                ids=[cp["id"]],
                documents=[cp["content"]],
                metadatas=[meta],
                embeddings=[chroma_vec],
            )

            async with async_session_factory() as us:
                await us.execute(
                    update(Chunk)
                    .where(Chunk.id == cp["id"])
                    .values(
                        vector_status="indexed",
                        embedding_model=getattr(embedding_client, "model", settings.embedding_model),
                        embedding_version="v2",
                        indexed_at=datetime.now(timezone.utc),
                    )
                )
                await us.commit()
            indexed += 1
        except Exception as exc:
            logger.warning("Chunk %s embed failed: %s", cp["id"][:8], exc)
            async with async_session_factory() as us:
                await us.execute(
                    update(Chunk).where(Chunk.id == cp["id"]).values(vector_status="failed")
                )
                await us.commit()
            failed += 1

    logger.info("_embed_chunks: %s → indexed=%d failed=%d", document_id[:8], indexed, failed)

    if failed > 0 and indexed == 0:
        await _set_failed_new_session(document_id, f"All {failed} chunks failed to embed")
    else:
        await _set_ready_new_session(
            document_id,
            error="" if failed == 0 else f"{failed} chunk(s) failed (partial index)",
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _doc_plain(doc: Document) -> dict:
    """Extract plain values from ORM object before entering executor."""
    return {
        "id": doc.id,
        "source_id": doc.source_id,
        "title": doc.title,
        "modality": doc.modality,
        "original_ref_uri": doc.original_ref_uri,
        "permission_level": doc.permission_level,
        "organization_id": doc.organization_id,
    }


def _parse_and_chunk_plain(
    doc_id: str,
    source_id: str,
    title: str,
    modality: str,
    original_ref_uri: str,
) -> tuple[dict, list[dict]]:
    """CPU-bound parse + chunk. Runs in executor — no async, no ORM objects."""
    file_path = _resolve_file_path(original_ref_uri)
    mime_type = _mime_from_modality(modality)

    if file_path and file_path.exists():
        extracted = chunking_client.extract_placeholder(file_path, mime_type, "")
    else:
        extracted = {"content": "", "modality": modality, "extraction_status": "empty"}

    content = extracted.get("content", "")
    ver_data = {
        "content": content,
        "content_sha256": _hash(content),
        "parser": "chunking_client",
        "extraction_status": extracted.get("extraction_status", "parsed"),
    }
    chunk_rows = chunking_client.chunk_document(
        source_id=source_id,
        title=title,
        content=content,
        modality=extracted.get("modality", modality),
        section_path=title,
        file_path=str(file_path) if file_path else "",
        mime_type=mime_type,
    )
    return ver_data, chunk_rows


def _resolve_file_path(original_ref_uri: str) -> Path | None:
    if not original_ref_uri or not original_ref_uri.startswith("upload://"):
        return None
    stored_name = original_ref_uri[len("upload://"):]
    return settings.upload_dir / stored_name


def _mime_from_modality(modality: str) -> str:
    return {"pdf": "application/pdf", "office": "application/octet-stream",
            "image": "image/jpeg", "text": "text/plain"}.get(modality, "text/plain")


def _get_chroma_collection():
    import chromadb
    client = chromadb.PersistentClient(path=str(settings.chroma_path))
    return client.get_or_create_collection(
        name=settings.chroma_collection_v2,
        metadata={"hnsw:space": settings.chroma_distance_space},
    )


def _hash(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


async def _set_failed_new_session(document_id: str, message: str) -> None:
    logger.error("Document %s failed: %s", document_id[:8], message)
    async with async_session_factory() as session:
        d = await session.get(Document, document_id)
        if d:
            d.status = "failed"
            d.error_message = message[:1990]
            d.updated_at = datetime.now(timezone.utc)
            await session.commit()


async def _set_ready_new_session(document_id: str, error: str = "") -> None:
    async with async_session_factory() as session:
        d = await session.get(Document, document_id)
        if d:
            d.status = "ready"
            d.error_message = error
            d.updated_at = datetime.now(timezone.utc)
            await session.commit()
    logger.info("Document %s → ready", document_id[:8])
