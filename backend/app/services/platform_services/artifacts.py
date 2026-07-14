from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_runtime import Artifact, ArtifactDependency, ArtifactVersion


class ArtifactService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_artifact(
        self,
        *,
        workflow_run_id: str,
        artifact_type: str,
        title: str,
        content_json: dict,
        file_path: str = "",
    ) -> Artifact:
        artifact = Artifact(
            workflow_run_id=workflow_run_id,
            artifact_type=artifact_type,
            title=title,
            content_json=content_json,
            file_path=file_path,
        )
        self.session.add(artifact)
        await self.session.flush()
        version = ArtifactVersion(
            artifact_id=artifact.id,
            version=1,
            content_json=content_json,
            file_path=file_path,
        )
        self.session.add(version)
        await self.session.flush()
        return artifact

    async def add_dependency(
        self,
        *,
        artifact_id: str,
        depends_on_artifact_id: str,
        dependency_type: str = "derived_from",
    ) -> ArtifactDependency:
        dependency = ArtifactDependency(
            artifact_id=artifact_id,
            depends_on_artifact_id=depends_on_artifact_id,
            dependency_type=dependency_type,
        )
        self.session.add(dependency)
        await self.session.flush()
        return dependency
