from app.services.agent_runtime import AgentBlueprintService
from app.services.agent_runtime.models import AgentRunRecord, WorkflowRunRecord


def test_agent_blueprints_are_valid_and_keep_future_agents_non_executable():
    service = AgentBlueprintService()

    service.validate()
    blueprints = service.list_blueprints()
    by_code = {item["code"]: item for item in blueprints}

    assert by_code["legacy_wenchuang_agent_v1"]["executable"] is True
    assert by_code["online_collection_agent"]["executable"] is False
    assert by_code["planning_outline_agent"]["phase"] == "future"
    assert by_code["cultural_ip_orchestrator_agent"]["role"] == "top_level"
    assert by_code["core_ip_sub_agent"]["parent_code"] == "cultural_ip_orchestrator_agent"


def test_agent_run_records_support_parent_child_relationships():
    workflow = WorkflowRunRecord(task_type="planning")
    parent = AgentRunRecord(
        workflow_run_id=workflow.id,
        agent_code="cultural_ip_orchestrator_agent",
    )
    child = AgentRunRecord(
        workflow_run_id=workflow.id,
        agent_code="core_ip_sub_agent",
        parent_agent_run_id=parent.id,
    )

    assert child.workflow_run_id == workflow.id
    assert child.parent_agent_run_id == parent.id
