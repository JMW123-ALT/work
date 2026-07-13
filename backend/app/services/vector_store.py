import hashlib
import json
import math
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.chunking_client import chunking_client
from app.services.embedding_client import embedding_client
from app.services.permissions import can_access

try:
    import chromadb
except ImportError as exc:  # pragma: no cover - exercised only before deps install
    chromadb = None
    CHROMA_IMPORT_ERROR = exc
else:
    CHROMA_IMPORT_ERROR = None


DATA_DIR = settings.data_dir
UPLOAD_DIR = settings.upload_dir
CHROMA_PATH = settings.chroma_path
SEED_FILE = DATA_DIR / "seed_documents.json"
DB_FILE = DATA_DIR / "vector_store.sqlite3"

PERMISSION_LEVELS = ("public", "free", "paid", "internal", "restricted")

DOCUMENT_COLUMNS = {
    "source_id": "TEXT PRIMARY KEY",
    "title": "TEXT NOT NULL",
    "content": "TEXT NOT NULL",
    "object_type": "TEXT NOT NULL",
    "permission_level": "TEXT NOT NULL",
    "access_channel": "TEXT NOT NULL",
    "original_ref_uri": "TEXT NOT NULL",
    "section_path": "TEXT NOT NULL",
    "vector_json": "TEXT NOT NULL DEFAULT '{}'",
    "modality": "TEXT NOT NULL DEFAULT 'text'",
    "file_name": "TEXT NOT NULL DEFAULT ''",
    "file_path": "TEXT NOT NULL DEFAULT ''",
    "mime_type": "TEXT NOT NULL DEFAULT ''",
    "file_size": "INTEGER NOT NULL DEFAULT 0",
    "file_sha256": "TEXT NOT NULL DEFAULT ''",
    "content_sha256": "TEXT NOT NULL DEFAULT ''",
    "chunk_count": "INTEGER NOT NULL DEFAULT 0",
    "extraction_status": "TEXT NOT NULL DEFAULT 'parsed'",
    "runtime": "INTEGER NOT NULL DEFAULT 0",
    "created_at": "TEXT NOT NULL",
    "updated_at": "TEXT NOT NULL",
}


class VectorStore:
    """SQLite document metadata plus a local Chroma vector index."""

    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)

        self.lock = threading.RLock()
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()
        self._create_chroma_collection()
        self._seed_if_needed()

    def _create_chroma_collection(self) -> None:
        if chromadb is None:
            raise RuntimeError(
                "chromadb is not installed. Run `pip install -r backend/requirements.txt`."
            ) from CHROMA_IMPORT_ERROR

        self.chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        self.collection = self.chroma_client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": settings.chroma_distance_space},
        )

    # Schema -----------------------------------------------------------------

    def _create_schema(self) -> None:
        with self.lock:
            column_sql = ",\n".join(
                f"{name} {spec}" for name, spec in DOCUMENT_COLUMNS.items()
            )
            self.conn.execute(f"CREATE TABLE IF NOT EXISTS documents ({column_sql})")
            existing = {
                row["name"]
                for row in self.conn.execute("PRAGMA table_info(documents)").fetchall()
            }
            for name, spec in DOCUMENT_COLUMNS.items():
                if name not in existing:
                    self.conn.execute(f"ALTER TABLE documents ADD COLUMN {name} {spec}")

            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    section_path TEXT NOT NULL,
                    content TEXT NOT NULL,
                    modality TEXT NOT NULL,
                    parser TEXT NOT NULL,
                    page_number INTEGER NOT NULL DEFAULT 0,
                    asset_path TEXT NOT NULL DEFAULT '',
                    asset_mime_type TEXT NOT NULL DEFAULT '',
                    embedding_modality TEXT NOT NULL DEFAULT 'text',
                    vector_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(source_id) REFERENCES documents(source_id)
                )
                """
            )
            chunk_existing = {
                row["name"]
                for row in self.conn.execute("PRAGMA table_info(chunks)").fetchall()
            }
            for name, spec in {
                "page_number": "INTEGER NOT NULL DEFAULT 0",
                "asset_path": "TEXT NOT NULL DEFAULT ''",
                "asset_mime_type": "TEXT NOT NULL DEFAULT ''",
                "embedding_modality": "TEXT NOT NULL DEFAULT 'text'",
            }.items():
                if name not in chunk_existing:
                    self.conn.execute(f"ALTER TABLE chunks ADD COLUMN {name} {spec}")
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_permission ON documents(permission_level)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_object_type ON documents(object_type)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_modality ON documents(modality)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_id)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunks_modality ON chunks(modality)"
            )
            self.conn.commit()

    def _seed_if_needed(self) -> None:
        if not SEED_FILE.exists():
            return
        seed_docs = json.loads(SEED_FILE.read_text(encoding="utf-8"))
        for doc in seed_docs:
            doc.setdefault("modality", "text")
            doc.setdefault("extraction_status", "parsed")
            self.upsert_document(doc, runtime=False)

    # CRUD -------------------------------------------------------------------

    def list_documents(self) -> list[dict]:
        with self.lock:
            rows = self.conn.execute(
                """
                SELECT source_id, title, content, object_type, permission_level,
                       access_channel, original_ref_uri, section_path, modality,
                       file_name, file_path, mime_type, file_size, chunk_count,
                       file_sha256, content_sha256, extraction_status, runtime,
                       created_at, updated_at
                FROM documents
                ORDER BY runtime ASC, updated_at DESC, source_id ASC
                """
            ).fetchall()
        return self._dedupe_documents([dict(row) for row in rows])

    def get_document(self, source_id: str) -> dict | None:
        with self.lock:
            row = self.conn.execute(
                """
                SELECT source_id, title, content, object_type, permission_level,
                       access_channel, original_ref_uri, section_path, modality,
                       file_name, file_path, mime_type, file_size, chunk_count,
                       file_sha256, content_sha256, extraction_status, runtime,
                       created_at, updated_at
                FROM documents WHERE source_id = ?
                """,
                (source_id,),
            ).fetchone()
        return dict(row) if row else None

    def add_document(self, payload: dict) -> dict:
        title = (payload.get("title") or "").strip()
        content = (payload.get("content") or "").strip()
        if not title or not content:
            raise ValueError("title and content are required")

        requested_modality = (payload.get("modality") or "text").lower()
        if requested_modality in ("pdf", "image", "office") and not payload.get(
            "file_path"
        ):
            raise ValueError("pdf, image and office documents must use file upload")

        doc = {
            "source_id": payload.get("source_id") or f"src-{uuid.uuid4().hex[:8]}",
            "title": title,
            "content": content,
            "object_type": payload.get("object_type") or "internal_doc",
            "permission_level": payload.get("permission_level") or "public",
            "access_channel": payload.get("access_channel") or "web",
            "original_ref_uri": payload.get("original_ref_uri") or "manual://local-entry",
            "section_path": payload.get("section_path") or title,
            "modality": requested_modality,
            "file_name": payload.get("file_name") or "",
            "file_path": payload.get("file_path") or "",
            "mime_type": payload.get("mime_type") or "",
            "file_size": int(payload.get("file_size") or 0),
            "file_sha256": payload.get("file_sha256") or "",
            "content_sha256": self._hash_text(content),
            "extraction_status": payload.get("extraction_status") or "parsed",
        }
        return self.upsert_document(doc, runtime=True)

    def add_file_document(self, fields: dict, file_item: dict) -> dict:
        original_name = file_item["filename"]
        file_bytes = file_item["data"]
        file_sha256 = self._hash_bytes(file_bytes)
        source_id = fields.get("source_id") or self._source_id_for_file_hash(file_sha256)
        source_id = source_id or f"src-file-{file_sha256[:12]}"
        safe_name = self._safe_file_name(original_name)
        stored_name = f"{source_id}-{safe_name}"
        file_path = UPLOAD_DIR / stored_name
        file_path.write_bytes(file_bytes)

        title = (fields.get("title") or Path(original_name).stem or "Untitled").strip()
        extracted = chunking_client.extract_placeholder(
            file_path,
            file_item.get("content_type", ""),
            fields.get("content", ""),
        )
        doc = {
            "source_id": source_id,
            "title": title,
            "content": extracted["content"],
            "object_type": fields.get("object_type") or "internal_doc",
            "permission_level": fields.get("permission_level") or "public",
            "access_channel": fields.get("access_channel") or "web_upload",
            "original_ref_uri": f"upload://{stored_name}",
            "section_path": fields.get("section_path") or title,
            "modality": fields.get("modality") or extracted["modality"],
            "file_name": original_name,
            "file_path": str(file_path),
            "mime_type": file_item.get("content_type", ""),
            "file_size": len(file_bytes),
            "file_sha256": file_sha256,
            "content_sha256": self._hash_text(extracted["content"]),
            "extraction_status": extracted["extraction_status"],
        }
        return self.upsert_document(doc, runtime=True)

    def upsert_document(self, doc: dict, runtime: bool = False) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        source_id = doc["source_id"]

        chunks = chunking_client.chunk_document(
            source_id=source_id,
            title=doc["title"],
            content=doc.get("content", ""),
            modality=doc.get("modality", "text"),
            section_path=doc.get("section_path", doc["title"]),
            file_path=doc.get("file_path", ""),
            mime_type=doc.get("mime_type", ""),
        )

        # 文档级聚合向量只取「标题 + 正文前 500 字」作为文档代表向量。
        # 不拼全文和所有 chunk —— 大文件会达数十万字，必然超过 DashScope
        # text-embedding-v3 的 8192 token 上限，导致 400 降级为本地向量。
        # 注意：该向量仅存 SQLite documents 表，Chroma 检索走 per-chunk 向量，不受影响。
        _AGGREGATE_PREVIEW = 500
        aggregate_text = " ".join(
            filter(
                None,
                [
                    doc.get("title", "").strip(),
                    (doc.get("content") or "")[:_AGGREGATE_PREVIEW].strip(),
                ],
            )
        )
        agg_vector = embedding_client.embed_text(aggregate_text)
        vector_json = json.dumps(agg_vector, ensure_ascii=False)

        chunk_vectors = []
        for chunk in chunks:
            raw_vector = self._embed_chunk(doc, chunk)
            chunk_vectors.append(
                {
                    "chunk": chunk,
                    "vector_json": json.dumps(raw_vector, ensure_ascii=False),
                    "embedding": self._to_chroma_embedding(raw_vector),
                }
            )

        with self.lock:
            try:
                existing = self.conn.execute(
                    "SELECT created_at FROM documents WHERE source_id = ?", (source_id,)
                ).fetchone()
                created_at = existing["created_at"] if existing else now
                old_chunk_ids = {
                    row["chunk_id"]
                    for row in self.conn.execute(
                        "SELECT chunk_id FROM chunks WHERE source_id = ?", (source_id,)
                    ).fetchall()
                }

                self.conn.execute(
                    """
                    INSERT INTO documents (
                        source_id, title, content, object_type, permission_level,
                        access_channel, original_ref_uri, section_path, vector_json,
                        modality, file_name, file_path, mime_type, file_size,
                        file_sha256, content_sha256, chunk_count, extraction_status,
                        runtime, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_id) DO UPDATE SET
                        title = excluded.title,
                        content = excluded.content,
                        object_type = excluded.object_type,
                        permission_level = excluded.permission_level,
                        access_channel = excluded.access_channel,
                        original_ref_uri = excluded.original_ref_uri,
                        section_path = excluded.section_path,
                        vector_json = excluded.vector_json,
                        modality = excluded.modality,
                        file_name = excluded.file_name,
                        file_path = excluded.file_path,
                        mime_type = excluded.mime_type,
                        file_size = excluded.file_size,
                        file_sha256 = excluded.file_sha256,
                        content_sha256 = excluded.content_sha256,
                        chunk_count = excluded.chunk_count,
                        extraction_status = excluded.extraction_status,
                        runtime = excluded.runtime,
                        updated_at = excluded.updated_at
                    """,
                    (
                        source_id,
                        doc["title"],
                        doc.get("content", ""),
                        doc.get("object_type", "internal_doc"),
                        doc.get("permission_level", "public"),
                        doc.get("access_channel", "web"),
                        doc.get("original_ref_uri", "manual://local-entry"),
                        doc.get("section_path", doc["title"]),
                        vector_json,
                        doc.get("modality", "text"),
                        doc.get("file_name", ""),
                        doc.get("file_path", ""),
                        doc.get("mime_type", ""),
                        int(doc.get("file_size") or 0),
                        doc.get("file_sha256", ""),
                        doc.get("content_sha256") or self._hash_text(doc.get("content", "")),
                        len(chunks),
                        doc.get("extraction_status", "parsed"),
                        1 if runtime else 0,
                        created_at,
                        now,
                    ),
                )

                self.conn.execute("DELETE FROM chunks WHERE source_id = ?", (source_id,))
                for item in chunk_vectors:
                    chunk = item["chunk"]
                    self.conn.execute(
                        """
                        INSERT INTO chunks (
                            chunk_id, source_id, chunk_index, section_path, content,
                            modality, parser, page_number, asset_path, asset_mime_type,
                            embedding_modality, vector_json, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            chunk["chunk_id"],
                            source_id,
                            chunk["chunk_index"],
                            chunk.get("section_path", doc["title"]),
                            chunk["content"],
                            chunk.get("modality", doc.get("modality", "text")),
                            chunk.get("parser", "placeholder_chunker"),
                            int(chunk.get("page_number") or 0),
                            chunk.get("asset_path", ""),
                            chunk.get("asset_mime_type", ""),
                            chunk.get("embedding_modality", "text"),
                            item["vector_json"],
                            now,
                        ),
                    )

                self._upsert_chroma_chunks(
                    doc=doc,
                    runtime=runtime,
                    created_at=created_at,
                    updated_at=now,
                    chunk_vectors=chunk_vectors,
                    old_chunk_ids=old_chunk_ids,
                )
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

        result = self.get_document(source_id)
        if result is None:
            raise RuntimeError(f"document {source_id} was not persisted")
        return result

    # Search -----------------------------------------------------------------

    def search(self, query: str, user_type: str = "visitor", top_k: int = 5) -> dict:
        query_vector = embedding_client.embed_text(query)
        query_embedding = self._to_chroma_embedding(query_vector)
        blocked_count = self._blocked_count(user_type)
        allowed_permissions = [
            level for level in PERMISSION_LEVELS if can_access(user_type, level)
        ]

        if not allowed_permissions:
            return {"items": [], "blockedCount": blocked_count}

        total_vectors = self.collection.count()
        if total_vectors <= 0:
            return {"items": [], "blockedCount": blocked_count}

        requested = max(int(top_k), 1)
        n_results = min(max(requested * 4, requested), total_vectors)
        query_kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if len(allowed_permissions) != len(PERMISSION_LEVELS):
            query_kwargs["where"] = {"permission_level": {"$in": allowed_permissions}}

        result = self.collection.query(**query_kwargs)
        items = self._dedupe_search_items(self._format_chroma_results(result))
        return {"items": items[:top_k], "blockedCount": blocked_count}

    def similarity_search_with_relevance_scores(
        self,
        query: str,
        *,
        user_type: str = "visitor",
        k: int = 5,
    ) -> list[tuple[dict, float]]:
        """LangChain-style Chroma search result without adding LangChain as a dependency."""

        result = self.search(query, user_type=user_type, top_k=k)
        pairs = []
        for item in result["items"]:
            document = {
                "page_content": item.get("content") or item.get("chunk_content") or "",
                "metadata": {
                    key: value
                    for key, value in item.items()
                    if key not in {"content", "chunk_content"}
                },
            }
            pairs.append((document, float(item.get("score") or 0.0)))
        return pairs

    def stats(self) -> dict:
        with self.lock:
            total = self.conn.execute("SELECT COUNT(*) AS n FROM documents").fetchone()["n"]
            chunks = self.conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()["n"]
            by_permission = self.conn.execute(
                "SELECT permission_level, COUNT(*) AS count FROM documents GROUP BY permission_level"
            ).fetchall()
            by_type = self.conn.execute(
                "SELECT object_type, COUNT(*) AS count FROM documents GROUP BY object_type"
            ).fetchall()
            by_modality = self.conn.execute(
                "SELECT modality, COUNT(*) AS count FROM documents GROUP BY modality"
            ).fetchall()

        return {
            "backend": "chroma-vector-store",
            "database": str(CHROMA_PATH),
            "metadataDatabase": str(DB_FILE),
            "collection": settings.chroma_collection,
            "distanceSpace": settings.chroma_distance_space,
            "uploads": str(UPLOAD_DIR),
            "total": total,
            "chunks": chunks,
            "vectors": self.collection.count(),
            "byPermission": [dict(row) for row in by_permission],
            "byType": [dict(row) for row in by_type],
            "byModality": [dict(row) for row in by_modality],
        }

    def rebuild_chroma_index(self) -> dict:
        """用 SQLite documents 重新生成 chunks 和 Chroma 向量索引。"""

        documents = self.list_documents()
        with self.lock:
            self.chroma_client.delete_collection(settings.chroma_collection)
            self._create_chroma_collection()

        rebuilt = 0
        for doc in documents:
            self.upsert_document(doc, runtime=bool(doc.get("runtime")))
            rebuilt += 1

        return {
            "documents": rebuilt,
            "vectors": self.collection.count(),
            "collection": settings.chroma_collection,
            "embeddingProvider": settings.embedding_provider,
            "embeddingModel": settings.embedding_model,
        }

    # Chroma helpers ---------------------------------------------------------

    def _upsert_chroma_chunks(
        self,
        doc: dict,
        runtime: bool,
        created_at: str,
        updated_at: str,
        chunk_vectors: list[dict],
        old_chunk_ids: set[str],
    ) -> None:
        if not chunk_vectors:
            if old_chunk_ids:
                self.collection.delete(ids=list(old_chunk_ids))
            return

        ids = [item["chunk"]["chunk_id"] for item in chunk_vectors]
        metadatas = [
            self._chunk_metadata(
                doc=doc,
                chunk=item["chunk"],
                chunk_count=len(chunk_vectors),
                runtime=runtime,
                created_at=created_at,
                updated_at=updated_at,
            )
            for item in chunk_vectors
        ]
        documents = [item["chunk"]["content"] for item in chunk_vectors]
        embeddings = [item["embedding"] for item in chunk_vectors]

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        stale_ids = old_chunk_ids - set(ids)
        if stale_ids:
            self.collection.delete(ids=list(stale_ids))

    def _chunk_metadata(
        self,
        doc: dict,
        chunk: dict,
        chunk_count: int,
        runtime: bool,
        created_at: str,
        updated_at: str,
    ) -> dict:
        raw = {
            "chunk_id": chunk["chunk_id"],
            "source_id": doc["source_id"],
            "chunk_index": int(chunk.get("chunk_index") or 0),
            "section_path": (
                chunk.get("section_path") or doc.get("section_path") or doc["title"]
            ),
            "modality": chunk.get("modality") or doc.get("modality", "text"),
            "parser": chunk.get("parser") or "placeholder_chunker",
            "page_number": int(chunk.get("page_number") or 0),
            "asset_path": chunk.get("asset_path", ""),
            "asset_mime_type": chunk.get("asset_mime_type", ""),
            "embedding_modality": chunk.get("embedding_modality", "text"),
            "title": doc["title"],
            "object_type": doc.get("object_type", "internal_doc"),
            "permission_level": doc.get("permission_level", "public"),
            "access_channel": doc.get("access_channel", "web"),
            "original_ref_uri": doc.get("original_ref_uri", "manual://local-entry"),
            "file_name": doc.get("file_name", ""),
            "mime_type": doc.get("mime_type", ""),
            "file_size": int(doc.get("file_size") or 0),
            "file_sha256": str(doc.get("file_sha256", "")),
            "content_sha256": str(doc.get("content_sha256", "")),
            "chunk_count": int(chunk_count),
            "extraction_status": doc.get("extraction_status", "parsed"),
            "runtime": 1 if runtime else 0,
            "created_at": created_at,
            "updated_at": updated_at,
        }
        return {key: self._metadata_value(value) for key, value in raw.items()}

    def _format_chroma_results(self, result: dict) -> list[dict]:
        ids = (result.get("ids") or [[]])[0] or []
        documents = (result.get("documents") or [[]])[0] or []
        metadatas = (result.get("metadatas") or [[]])[0] or []
        distances = (result.get("distances") or [[]])[0] or []

        items = []
        for index, chunk_id in enumerate(ids):
            metadata = dict(metadatas[index] or {}) if index < len(metadatas) else {}
            content = documents[index] if index < len(documents) else ""
            distance = distances[index] if index < len(distances) else None
            score = self._score_from_distance(distance)

            section_path = str(metadata.get("section_path", ""))
            modality = str(metadata.get("modality", "text"))
            item = {
                "chunk_id": chunk_id,
                "chunk_index": self._metadata_int(metadata, "chunk_index"),
                "chunk_section_path": section_path,
                "chunk_content": content,
                "chunk_modality": modality,
                "parser": str(metadata.get("parser", "")),
                "page_number": self._metadata_int(metadata, "page_number"),
                "asset_path": str(metadata.get("asset_path", "")),
                "asset_mime_type": str(metadata.get("asset_mime_type", "")),
                "embedding_modality": str(metadata.get("embedding_modality", "text")),
                "source_id": str(metadata.get("source_id", "")),
                "title": str(metadata.get("title", "")),
                "object_type": str(metadata.get("object_type", "internal_doc")),
                "permission_level": str(metadata.get("permission_level", "public")),
                "access_channel": str(metadata.get("access_channel", "web")),
                "original_ref_uri": str(metadata.get("original_ref_uri", "")),
                "section_path": section_path,
                "modality": modality,
                "file_name": str(metadata.get("file_name", "")),
                "mime_type": str(metadata.get("mime_type", "")),
                "file_size": self._metadata_int(metadata, "file_size"),
                "file_sha256": str(metadata.get("file_sha256", "")),
                "content_sha256": str(metadata.get("content_sha256", "")),
                "chunk_count": self._metadata_int(metadata, "chunk_count"),
                "extraction_status": str(metadata.get("extraction_status", "parsed")),
                "runtime": self._metadata_int(metadata, "runtime"),
                "created_at": str(metadata.get("created_at", "")),
                "updated_at": str(metadata.get("updated_at", "")),
                "score": round(score, 4),
                "snippet": content[:180],
                "content": content,
            }
            items.append(item)

        return items

    def _embed_chunk(self, doc: dict, chunk: dict) -> dict:
        text = f"{doc['title']} {chunk['content']}"
        asset_path = str(chunk.get("asset_path") or "")
        if asset_path:
            return embedding_client.embed_multimodal(
                text,
                image_path=asset_path,
                mime_type=str(chunk.get("asset_mime_type") or doc.get("mime_type") or ""),
            )
        return embedding_client.embed_text(text)

    def _blocked_count(self, user_type: str) -> int:
        with self.lock:
            rows = self.conn.execute(
                """
                SELECT source_id, permission_level, chunk_count
                FROM documents
                WHERE chunk_count > 0
                """
            ).fetchall()

        blocked_sources = {
            row["source_id"]
            for row in rows
            if not can_access(user_type, row["permission_level"])
        }
        return len(blocked_sources)

    def _to_chroma_embedding(self, vector: dict) -> list[float]:
        if vector.get("type") == "dense":
            data = [float(value) for value in vector.get("data", [])]
            return self._non_zero_vector(data)

        sparse = vector.get("data", vector)
        dimension = max(16, int(settings.chroma_local_embedding_dimension or 1024))
        dense = [0.0] * dimension
        if isinstance(sparse, dict):
            for token, weight in sparse.items():
                digest = hashlib.blake2b(
                    str(token).encode("utf-8"), digest_size=8
                ).digest()
                index = int.from_bytes(digest, "big") % dimension
                sign = 1.0 if digest[0] % 2 == 0 else -1.0
                dense[index] += sign * float(weight)
        return self._non_zero_vector(dense, normalize=True)

    def _non_zero_vector(
        self, values: list[float], normalize: bool = False
    ) -> list[float]:
        if not values:
            values = [0.0] * max(
                16, int(settings.chroma_local_embedding_dimension or 1024)
            )

        norm = math.sqrt(sum(value * value for value in values))
        if norm == 0:
            values[0] = 1.0
            norm = 1.0

        if normalize:
            return [value / norm for value in values]
        return values

    def _score_from_distance(self, distance: Any) -> float:
        if distance is None:
            return 0.0
        try:
            value = float(distance)
        except (TypeError, ValueError):
            return 0.0
        if settings.chroma_distance_space == "cosine":
            return max(0.0, 1.0 - value)
        return 1.0 / (1.0 + max(0.0, value))

    def _metadata_value(self, value: Any) -> str | int | float | bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        if isinstance(value, float):
            return value
        if value is None:
            return ""
        return str(value)

    def _metadata_int(self, metadata: dict, key: str) -> int:
        try:
            return int(metadata.get(key) or 0)
        except (TypeError, ValueError):
            return 0

    def _source_id_for_file_hash(self, file_sha256: str) -> str | None:
        if not file_sha256:
            return None
        with self.lock:
            row = self.conn.execute(
                """
                SELECT source_id
                FROM documents
                WHERE file_sha256 = ?
                ORDER BY updated_at DESC, source_id ASC
                LIMIT 1
                """,
                (file_sha256,),
            ).fetchone()
        return str(row["source_id"]) if row else None

    def _dedupe_documents(self, items: list[dict]) -> list[dict]:
        seen: set[str] = set()
        unique: list[dict] = []
        for item in items:
            key = self._document_dedupe_key(item)
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    def _document_dedupe_key(self, item: dict) -> str:
        file_sha256 = str(item.get("file_sha256") or "")
        if file_sha256:
            return f"file-sha:{file_sha256}"
        file_name = str(item.get("file_name") or "").strip().lower()
        file_size = int(item.get("file_size") or 0)
        title = str(item.get("title") or "").strip().lower()
        if file_name and file_size:
            return f"file-meta:{title}:{file_name}:{file_size}"
        content_sha256 = str(item.get("content_sha256") or "")
        if content_sha256:
            return f"content-sha:{content_sha256}"
        return f"source:{item.get('source_id')}"

    def _dedupe_search_items(self, items: list[dict]) -> list[dict]:
        seen: set[str] = set()
        unique: list[dict] = []
        for item in items:
            asset_path = str(item.get("asset_path") or "")
            if asset_path:
                key = f"asset:{asset_path}:{item.get('chunk_id')}"
            else:
                content = str(item.get("content") or item.get("chunk_content") or "")
                normalized = re.sub(r"\s+", "", content)
                key = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    def _hash_bytes(self, value: bytes) -> str:
        return hashlib.sha256(value or b"").hexdigest()

    def _hash_text(self, value: str) -> str:
        normalized = re.sub(r"\s+", "", value or "")
        if not normalized:
            return ""
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _safe_file_name(self, filename: str) -> str:
        clean = re.sub(
            r"[^0-9A-Za-z._\-\u4e00-\u9fff]+", "_", filename or "upload.bin"
        )
        return clean[:120] or "upload.bin"


vector_store = VectorStore()
