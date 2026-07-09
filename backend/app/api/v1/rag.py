"""
RAG 搜索与问答路由
"""
from fastapi import APIRouter

from app.api.deps import RAGServiceDep
from app.schemas.rag import AskRequest, SearchRequest, SearchResponse

router = APIRouter(tags=["检索与问答"])


@router.post("/search", response_model=SearchResponse, summary="语义检索")
def search(req: SearchRequest, svc: RAGServiceDep):
    return svc.search(req.model_dump())


@router.post("/ask", summary="RAG 问答")
def ask(req: AskRequest, svc: RAGServiceDep):
    return svc.ask(req.model_dump())
