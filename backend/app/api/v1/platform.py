from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.db.session import async_session_factory
from app.schemas.rag import SearchRequest, SearchResponse
from app.schemas.platform import (
    AgentBlueprintsResponse,
    AgentRuntimeSchemaResponse,
    DatabaseHealthResponse,
    PlatformIngestResponse,
    PlatformTextIngestRequest,
    ResourceCategoriesResponse,
    ResourceGovernanceResponse,
    VectorIndexRunRequest,
    VectorIndexRunResponse,
)
from app.services.agent_runtime import AgentBlueprintService
from app.services.platform_services import (
    ChromaIndexService,
    DatabaseReadinessService,
    DocumentIngestionService,
    RetrievalService,
)
from app.services.resource_library.governance import governance_snapshot
from app.services.resource_library.taxonomy import ResourceCategoryService

router = APIRouter(tags=["平台框架"])


@router.get(
    "/resource-categories",
    response_model=ResourceCategoriesResponse,
    summary="资源库分类种子树",
)
def list_resource_categories():
    return {"items": ResourceCategoryService().flatten()}


@router.get(
    "/resource-governance/options",
    response_model=ResourceGovernanceResponse,
    summary="资源库治理维度",
)
def resource_governance_options():
    return {"options": governance_snapshot()}


@router.get(
    "/agent-runtime/blueprints",
    response_model=AgentBlueprintsResponse,
    summary="Agent 平台蓝图",
)
def list_agent_blueprints():
    return {"items": AgentBlueprintService().list_blueprints()}


@router.get(
    "/agent-runtime/schema",
    response_model=AgentRuntimeSchemaResponse,
    summary="Agent 运行记录框架",
)
def agent_runtime_schema():
    return {
        "workflow_statuses": [
            "pending",
            "running",
            "waiting_user",
            "succeeded",
            "failed",
            "cancelled",
        ],
        "runtime_tables": [
            "workflow_runs",
            "agent_runs",
            "agent_run_steps",
            "agent_evidence",
            "reviews",
            "artifacts",
            "artifact_versions",
            "artifact_dependencies",
            "prompt_templates",
            "platform_profiles",
            "intelligence_items",
        ],
        "note": "Framework only: future business agents are not executable in this stage.",
    }


@router.get(
    "/platform/database/health",
    response_model=DatabaseHealthResponse,
    summary="PostgreSQL readiness check",
)
async def database_health():
    return await DatabaseReadinessService().check()


@router.post(
    "/platform/resources/text",
    response_model=PlatformIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="PostgreSQL v2 text resource ingestion",
)
async def ingest_text_resource(req: PlatformTextIngestRequest):
    if async_session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DATABASE_URL is not configured",
        )

    async with async_session_factory() as session:
        result = await DocumentIngestionService(session).create_text_document(
            organization_id=req.organization_id,
            project_id=req.project_id,
            source_id=req.source_id,
            title=req.title,
            content=req.content,
            modality=req.modality,
        )
        await session.commit()
        return result


@router.post(
    "/platform/resources/file",
    response_model=PlatformIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="PostgreSQL v2 file resource ingestion",
)
async def ingest_file_resource(
    file: Annotated[UploadFile, File()],
    organization_id: Annotated[str, Form()],
    title: Annotated[str | None, Form()] = None,
    project_id: Annotated[str | None, Form()] = None,
    source_id: Annotated[str | None, Form()] = None,
    description: Annotated[str, Form()] = "",
):
    if async_session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DATABASE_URL is not configured",
        )

    file_bytes = await file.read()
    async with async_session_factory() as session:
        result = await DocumentIngestionService(session).create_file_document(
            organization_id=organization_id,
            project_id=project_id,
            source_id=source_id,
            title=title,
            file_name=file.filename or "unnamed",
            file_bytes=file_bytes,
            mime_type=file.content_type or "",
            description=description,
        )
        await session.commit()
        return result


@router.post(
    "/platform/vector-index/run",
    response_model=VectorIndexRunResponse,
    summary="Index PostgreSQL chunks into Chroma v2",
)
async def run_vector_index(req: VectorIndexRunRequest):
    if async_session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DATABASE_URL is not configured",
        )

    async with async_session_factory() as session:
        result = await ChromaIndexService(session).index_pending(limit=req.limit)
        await session.commit()
        return result


@router.post(
    "/platform/search",
    response_model=SearchResponse,
    summary="Search Chroma v2 with PostgreSQL metadata",
)
async def search_v2_resources(req: SearchRequest):
    if async_session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DATABASE_URL is not configured",
        )

    async with async_session_factory() as session:
        return await RetrievalService(session).search(req.model_dump())
