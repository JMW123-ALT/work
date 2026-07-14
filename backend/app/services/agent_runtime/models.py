"""Typed runtime records for the future PostgreSQL-backed Agent platform."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


RuntimeStatus = Literal[
    "pending",
    "running",
    "waiting_user",
    "succeeded",
    "failed",
    "cancelled",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


class AgentBlueprint(BaseModel):
    code: str
    name: str
    role: Literal["top_level", "sub_agent", "tool", "legacy"]
    phase: Literal["current", "future"]
    parent_code: str | None = None
    output_artifacts: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    executable: bool = False


class WorkflowRunRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("workflow"))
    project_id: str | None = None
    user_id: str | None = None
    task_type: str = ""
    status: RuntimeStatus = "pending"
    input_payload: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AgentRunRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("agent_run"))
    workflow_run_id: str
    agent_code: str
    parent_agent_run_id: str | None = None
    status: RuntimeStatus = "pending"
    input_payload: dict = Field(default_factory=dict)
    output_payload: dict = Field(default_factory=dict)
    error_message: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AgentRunStepRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("agent_step"))
    agent_run_id: str
    node_name: str
    status: RuntimeStatus = "pending"
    input_payload: dict = Field(default_factory=dict)
    output_payload: dict = Field(default_factory=dict)
    error_message: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class EvidenceRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("evidence"))
    workflow_run_id: str
    agent_run_id: str | None = None
    artifact_id: str | None = None
    document_id: str | None = None
    chunk_id: str | None = None
    source_id: str | None = None
    page_number: int = 0
    quote: str = ""
    score: float = 0
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class ReviewRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("review"))
    workflow_run_id: str
    artifact_id: str | None = None
    reviewer_id: str | None = None
    status: Literal["pending", "approved", "changes_requested", "rejected"] = "pending"
    comments: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ArtifactRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("artifact"))
    workflow_run_id: str
    artifact_type: str
    title: str
    status: Literal["draft", "active", "archived", "deleted"] = "draft"
    content_json: dict = Field(default_factory=dict)
    file_path: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ArtifactVersionRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("artifact_version"))
    artifact_id: str
    version: int
    content_json: dict = Field(default_factory=dict)
    file_path: str = ""
    created_at: datetime = Field(default_factory=utc_now)


class ArtifactDependencyRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("artifact_dep"))
    artifact_id: str
    depends_on_artifact_id: str
    dependency_type: str = "derived_from"
    created_at: datetime = Field(default_factory=utc_now)


class PromptTemplateRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("prompt"))
    code: str
    version: str
    agent_code: str
    content: str
    status: Literal["draft", "active", "archived"] = "draft"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class PlatformProfileRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("platform"))
    code: str
    name: str
    rules_json: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class IntelligenceItemRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("intel"))
    project_id: str | None = None
    source: str = ""
    topic: str = ""
    content: str = ""
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
