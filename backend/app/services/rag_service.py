from app.services.audit import audit_store
from app.services.llm_client import llm_client
from app.services.permissions import normalize_user_type, permission_notice
from app.services.rerank_client import rerank_client
from app.services.vector_store import vector_store


class RAGService:
    def search(self, payload: dict) -> dict:
        query = (payload.get("query") or "").strip()
        if not query:
            raise ValueError("query is required")
        user_type = normalize_user_type(payload.get("user_type", "visitor"))
        top_k = int(payload.get("top_k", 5))
        retrieval_top_k = int(payload.get("retrieval_top_k") or max(top_k * 4, top_k))
        min_confidence = float(payload.get("min_confidence", 0.7))

        retrieval = vector_store.search(query, user_type=user_type, top_k=retrieval_top_k)
        reranked = rerank_client.rerank(query, retrieval["items"], top_n=top_k)
        search_items = [
            item
            for item in (_to_agent_search_item(raw_item) for raw_item in reranked["items"])
            if item["confidence"] >= min_confidence
        ]

        audit_store.record(
            "search",
            user_type,
            {
                "query": query,
                "retrievalCount": len(retrieval["items"]),
                "resultCount": len(search_items),
                "blockedCount": retrieval["blockedCount"],
                "rerankMode": reranked["mode"],
                "rerankModel": reranked["model"],
                "minConfidence": min_confidence,
            },
        )

        return {
            "items": search_items,
            "blockedCount": retrieval["blockedCount"],
            "permissionNotice": permission_notice(retrieval["blockedCount"]),
            "rerank": {"mode": reranked["mode"], "model": reranked["model"]},
        }

    def ask(self, payload: dict) -> dict:
        question = (payload.get("question") or "").strip()
        if not question:
            raise ValueError("question is required")
        user_type = normalize_user_type(payload.get("user_type", "visitor"))
        top_k = int(payload.get("top_k", 5))
        retrieval_top_k = int(payload.get("retrieval_top_k") or max(top_k * 4, top_k))

        retrieval = vector_store.search(question, user_type=user_type, top_k=retrieval_top_k)
        reranked = rerank_client.rerank(question, retrieval["items"], top_n=top_k)
        notice = permission_notice(retrieval["blockedCount"])
        llm_result = llm_client.generate_answer(question, reranked["items"], notice)

        audit = audit_store.record(
            "ask",
            user_type,
            {
                "question": question,
                "retrievalCount": len(retrieval["items"]),
                "sourceCount": len(reranked["items"]),
                "blockedCount": retrieval["blockedCount"],
                "rerankMode": reranked["mode"],
                "rerankModel": reranked["model"],
                "llmMode": llm_result["mode"],
            },
        )

        return {
            **llm_result,
            "sources": reranked["items"],
            "blockedCount": retrieval["blockedCount"],
            "permissionNotice": notice,
            "rerank": {"mode": reranked["mode"], "model": reranked["model"]},
            "traceId": audit["trace_id"],
        }


rag_service = RAGService()


def _to_agent_search_item(item: dict) -> dict:
    """把后端内部 chunk 命中结果转换成 Agent 可直接使用的 Evidence 字段。"""

    source_id = str(item.get("source_id") or "")
    confidence = _confidence(item)
    permission_level = str(item.get("permission_level") or "public")
    metadata_keys = (
        "chunk_id",
        "source_id",
        "chunk_index",
        "title",
        "section_path",
        "object_type",
        "permission_level",
        "access_channel",
        "original_ref_uri",
        "modality",
        "parser",
        "file_name",
        "mime_type",
        "file_size",
        "chunk_count",
        "extraction_status",
        "runtime",
        "created_at",
        "updated_at",
        "score",
        "rerank_score",
        "rerank_rank",
    )

    return {
        "text": str(item.get("content") or item.get("chunk_content") or item.get("snippet") or ""),
        "source": f"shujuku:{source_id}" if source_id else "shujuku:unknown",
        "category": str(item.get("object_type") or ""),
        "culture_theme": str(item.get("title") or item.get("section_path") or ""),
        "confidence": confidence,
        "copyright_status": _copyright_status(permission_level),
        "risk_level": _risk_level(permission_level),
        "metadata": {key: item.get(key) for key in metadata_keys if key in item},
    }


def _confidence(item: dict) -> float:
    raw_score = item.get("rerank_score", item.get("score", 0))
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        score = 0.0
    return round(min(max(score, 0.0), 1.0), 4)


def _copyright_status(permission_level: str) -> str:
    if permission_level == "public":
        return "public_domain"
    if permission_level in {"free", "paid", "internal"}:
        return "authorized"
    return "unknown"


def _risk_level(permission_level: str) -> str:
    if permission_level in {"internal", "restricted"}:
        return "medium"
    return "low"
