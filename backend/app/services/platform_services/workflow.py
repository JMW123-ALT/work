from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_runtime import AgentRun, WorkflowRun
from app.repositories.workflow import WorkflowRepository


class WorkflowService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.workflows = WorkflowRepository(session)

    async def start_workflow(
        self,
        *,
        task_type: str,
        input_payload: dict,
        project_id: str | None = None,
        user_id: str | None = None,
    ) -> WorkflowRun:
        workflow = WorkflowRun(
            project_id=project_id,
            user_id=user_id,
            task_type=task_type,
            status="running",
            input_payload=input_payload,
        )
        return await self.workflows.add(workflow)

    async def start_agent_run(
        self,
        *,
        workflow_run_id: str,
        agent_code: str,
        input_payload: dict,
        parent_agent_run_id: str | None = None,
    ) -> AgentRun:
        agent_run = AgentRun(
            workflow_run_id=workflow_run_id,
            parent_agent_run_id=parent_agent_run_id,
            agent_code=agent_code,
            status="running",
            input_payload=input_payload,
        )
        self.session.add(agent_run)
        await self.session.flush()
        return agent_run
