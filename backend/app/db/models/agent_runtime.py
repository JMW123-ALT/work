from sqlalchemy import ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class WorkflowRun(IdMixin, TimestampMixin, Base):
    __tablename__ = "workflow_runs"

    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    input_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")


class AgentRun(IdMixin, TimestampMixin, Base):
    __tablename__ = "agent_runs"

    workflow_run_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_agent_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    agent_code: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    input_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")


class AgentRunStep(IdMixin, TimestampMixin, Base):
    __tablename__ = "agent_run_steps"

    agent_run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    input_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")


class AgentEvidence(IdMixin, TimestampMixin, Base):
    __tablename__ = "agent_evidence"

    workflow_run_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    artifact_id: Mapped[str | None] = mapped_column(
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_id: Mapped[str | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    chunk_id: Mapped[str | None] = mapped_column(
        ForeignKey("chunks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_id: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    page_number: Mapped[int] = mapped_column(nullable=False, default=0)
    quote: Mapped[str] = mapped_column(Text, nullable=False, default="")
    score: Mapped[float] = mapped_column(nullable=False, default=0)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class Review(IdMixin, TimestampMixin, Base):
    __tablename__ = "reviews"

    workflow_run_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_id: Mapped[str | None] = mapped_column(
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewer_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    comments: Mapped[str] = mapped_column(Text, nullable=False, default="")


class Artifact(IdMixin, TimestampMixin, Base):
    __tablename__ = "artifacts"

    workflow_run_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_type: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    content_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False, default="")


class ArtifactVersion(IdMixin, TimestampMixin, Base):
    __tablename__ = "artifact_versions"

    artifact_id: Mapped[str] = mapped_column(
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(nullable=False)
    content_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False, default="")

    __table_args__ = (
        UniqueConstraint("artifact_id", "version", name="uq_artifact_versions_version"),
    )


class ArtifactDependency(IdMixin, TimestampMixin, Base):
    __tablename__ = "artifact_dependencies"

    artifact_id: Mapped[str] = mapped_column(
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    depends_on_artifact_id: Mapped[str] = mapped_column(
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dependency_type: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        default="derived_from",
    )

    __table_args__ = (
        UniqueConstraint(
            "artifact_id",
            "depends_on_artifact_id",
            "dependency_type",
            name="uq_artifact_dependencies_relation",
        ),
    )


class PromptTemplate(IdMixin, TimestampMixin, Base):
    __tablename__ = "prompt_templates"

    code: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    agent_code: Mapped[str] = mapped_column(String(120), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")

    __table_args__ = (
        UniqueConstraint("code", "version", name="uq_prompt_templates_code_version"),
    )


class PlatformProfile(IdMixin, TimestampMixin, Base):
    __tablename__ = "platform_profiles"

    code: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    rules_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class IntelligenceItem(IdMixin, TimestampMixin, Base):
    __tablename__ = "intelligence_items"

    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    topic: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
