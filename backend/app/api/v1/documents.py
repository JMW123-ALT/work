from fastapi import APIRouter

from app.api.deps import VectorStoreDep

router = APIRouter(tags=["文档管理"])


@router.get("/documents", summary="获取所有文档列表")
def list_documents(vs: VectorStoreDep):
    return {"items": vs.list_documents()}
