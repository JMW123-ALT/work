"""Platform framework response schemas."""

from pydantic import BaseModel, Field


class ResourceCategoryItem(BaseModel):
    code: str
    name: str
    parent_code: str | None = None
    depth: int = 0
    sort_order: int = 0
    is_active: bool = True


class ResourceCategoriesResponse(BaseModel):
    items: list[ResourceCategoryItem]


class ResourceGovernanceResponse(BaseModel):
    options: dict[str, list[str]]


class AgentBlueprintItem(BaseModel):
    code: str
    name: str
    role: str
    phase: str
    parent_code: str | None = None
    output_artifacts: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    executable: bool = False


class AgentBlueprintsResponse(BaseModel):
    items: list[AgentBlueprintItem]


class AgentRuntimeSchemaResponse(BaseModel):
    workflow_statuses: list[str]
    runtime_tables: list[str]
    note: str


class DatabaseHealthResponse(BaseModel):
    configured: bool
    reachable: bool
    status: str
    alembic_revision: str | None = None
    message: str


class PlatformTextIngestRequest(BaseModel):
    organization_id: str
    source_id: str
    title: str
    content: str
    project_id: str | None = None
    modality: str = "text"


class PlatformIngestResponse(BaseModel):
    document_id: str
    source_id: str
    title: str
    duplicate: bool
    chunk_count: int
    version_id: str | None = None
    file_id: str | None = None
    vector_status: str


class VectorIndexRunRequest(BaseModel):
    limit: int = Field(default=100, ge=1, le=500)


class VectorIndexRunResponse(BaseModel):
    collection: str
    indexed: int
    failed: int
    errors: list[dict[str, str]] = Field(default_factory=list)
