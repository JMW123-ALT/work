"""
v1 路由总入口：将所有子路由汇总
"""
from fastapi import APIRouter

from app.api.v1 import documents, health, ingest, rag

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(documents.router)
api_router.include_router(ingest.router)
api_router.include_router(rag.router)
