from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_runtime import AgentEvidence, AgentRun, Artifact, WorkflowRun
from app.repositories.base import BaseRepository


class WorkflowRepository(BaseRepository[WorkflowRun]):
    model = WorkflowRun

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_agent_runs(self, workflow_run_id: str) -> list[AgentRun]:
        result = await self.session.execute(
            select(AgentRun)
            .where(AgentRun.workflow_run_id == workflow_run_id)
            .order_by(AgentRun.created_at)
        )
        return list(result.scalars().all())

    async def list_artifacts(self, workflow_run_id: str) -> list[Artifact]:
        result = await self.session.execute(
            select(Artifact)
            .where(Artifact.workflow_run_id == workflow_run_id)
            .order_by(Artifact.created_at)
        )
        return list(result.scalars().all())

    async def list_evidence(self, workflow_run_id: str) -> list[AgentEvidence]:
        result = await self.session.execute(
            select(AgentEvidence)
            .where(AgentEvidence.workflow_run_id == workflow_run_id)
            .order_by(AgentEvidence.created_at)
        )
        return list(result.scalars().all())
