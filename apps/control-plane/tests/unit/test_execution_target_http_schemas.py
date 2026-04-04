from __future__ import annotations

from uuid import uuid4

from app.modules.experiments.adapters.inbound.http.schemas import ExperimentSpecRequest
from app.modules.runs.adapters.inbound.http.schemas import RunCreateRequest, RunResponse
from app.modules.runs.domain.models import RunRecord
from app.modules.shared.domain.enums import AdapterKind
from app.modules.shared.domain.models import ExecutionTarget


def test_run_create_request_to_domain_preserves_execution_target() -> None:
    request = RunCreateRequest.model_validate(
        {
            "project": "migration-check",
            "dataset": "framework-ds",
            "agent_id": "triage-bot",
            "input_summary": "framework coverage",
            "prompt": "Inspect the latest run.",
            "execution_target": {
                "kind": "endpoint",
                "display_name": "staging",
                "target_ref": "endpoint://staging",
                "metadata": {"base_url": "https://staging.example.com"},
            },
        }
    )

    domain = request.to_domain()

    assert domain.execution_target == ExecutionTarget(
        kind="endpoint",
        display_name="staging",
        target_ref="endpoint://staging",
        metadata={"base_url": "https://staging.example.com"},
    )


def test_experiment_spec_request_to_domain_preserves_execution_target() -> None:
    dataset_version_id = uuid4()
    request = ExperimentSpecRequest.model_validate(
        {
            "dataset_version_id": str(dataset_version_id),
            "published_agent_id": "triage-bot",
            "model_settings": {"model": "gpt-5.4-mini"},
            "execution_target": {
                "kind": "workspace_project",
                "display_name": "migration-check",
                "target_ref": "file:///tmp/migration-check.tar.gz",
                "metadata": {"cwd": "/workspace/project/repo"},
            },
        }
    )

    domain = request.to_domain()

    assert domain.execution_target == ExecutionTarget(
        kind="workspace_project",
        display_name="migration-check",
        target_ref="file:///tmp/migration-check.tar.gz",
        metadata={"cwd": "/workspace/project/repo"},
    )


def test_run_response_from_domain_exposes_execution_target() -> None:
    run = RunRecord(
        project="migration-check",
        input_summary="framework coverage",
        agent_id="triage-bot",
        model="gpt-5.4-mini",
        agent_type=AdapterKind.LANGCHAIN,
        execution_target=ExecutionTarget(
            kind="workspace_project",
            display_name="migration-check",
            target_ref="file:///tmp/migration-check.tar.gz",
            metadata={"cwd": "/workspace/project/repo"},
        ),
    )

    response = RunResponse.from_domain(run)

    assert response.execution_target == run.execution_target
