"""
v1 路由总入口：将所有子路由汇总
"""
from fastapi import APIRouter

from app.api.v1 import (
    agent,
    documents,
    health,
    ingest,
    ip,
    planning_image,
    platform,
    promotion,
    rag,
    websearch,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(agent.router)
api_router.include_router(platform.router)
api_router.include_router(planning_image.router)
api_router.include_router(promotion.router)
api_router.include_router(ip.router)
api_router.include_router(documents.router, include_in_schema=False)
api_router.include_router(ingest.router, include_in_schema=False)
api_router.include_router(rag.router, include_in_schema=False)
api_router.include_router(websearch.router, include_in_schema=False)
