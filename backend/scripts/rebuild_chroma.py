"""从 SQLite 文档库重建 Chroma 向量索引。

运行前请确认根目录 `.env` 中已经配置：

EMBEDDING_PROVIDER=dashscope
EMBEDDING_MODEL=qwen3-vl-embedding
EMBEDDING_API_KEY=...
EMBEDDING_BASE_URL=https://.../api/v1
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def delete_existing_collection() -> None:
    import chromadb
    from app.core.config import settings

    client = chromadb.PersistentClient(path=str(settings.chroma_path))
    try:
        client.delete_collection(settings.chroma_collection)
    except Exception:
        return


def main() -> None:
    delete_existing_collection()
    from app.services.vector_store import vector_store

    result = vector_store.rebuild_chroma_index()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
