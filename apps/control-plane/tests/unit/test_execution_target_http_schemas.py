from __future__ import annotations

from uuid import uuid4

import pytest
from app.modules.experiments.adapters.inbound.http.schemas import ExperimentSpecRequest
from app.modules.runs.adapters.inbound.http.schemas import RunCreateRequest, RunResponse
from app.modules.runs.domain.models import RunRecord
from app.modules.shared.domain.enums import AdapterKind
from app.modules.shared.domain.models import ExecutionProfile, ExecutionTarget
from pydantic import ValidationError


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


def test_run_create_request_canonical_execution_binding_shape_is_preserved() -> None:
    request = RunCreateRequest.model_validate(
        {
            "project": "migration-check",
            "agent_id": "triage-bot",
            "input_summary": "canonical executor payload",
            "prompt": "Inspect the latest run.",
            "executor_config": {
                "backend": "external-runner",
                "execution_binding": {
                    "runner_backend": "docker-container",
                    "runner_image": "atlas-claude-validation:local",
                    "artifact_path": "/tmp/artifacts",
                    "config": {
                        "timeout_seconds": 900,
                        "max_steps": 64,
                        "concurrency": 2,
                        "resources": {"cpu": "1000m", "memory": "1Gi"},
                        "region": "us-east-1",
                    },
                },
            },
        }
    )

    domain = request.to_domain()

    assert domain.executor_config == ExecutionProfile(
        backend="external-runner",
        tracing_backend="state",
    )
    assert domain.execution_binding is not None
    assert domain.execution_binding.runner_backend == "docker-container"
    assert domain.execution_binding.runner_image == "atlas-claude-validation:local"
    assert domain.execution_binding.artifact_path == "/tmp/artifacts"
    assert domain.execution_binding.config == {
        "timeout_seconds": 900,
        "max_steps": 64,
        "concurrency": 2,
        "resources": {"cpu": "1000m", "memory": "1Gi"},
        "region": "us-east-1",
    }


def test_run_create_request_rejects_legacy_executor_shape() -> None:
    with pytest.raises(ValidationError):
        RunCreateRequest.model_validate(
            {
                "project": "migration-check",
                "agent_id": "triage-bot",
                "input_summary": "legacy executor payload",
                "prompt": "Inspect the latest run.",
                "executor_config": {
                    "backend": "external-runner",
                    "runner_image": "atlas-claude-validation:local",
                    "metadata": {"runner_backend": "docker-container"},
                },
            }
        )


def test_execution_profile_domain_model_no_longer_coerces_legacy_executor_shape() -> None:
    with pytest.raises(ValidationError):
        ExecutionProfile.model_validate(
            {
                "backend": "external-runner",
                "runner_image": "atlas-claude-validation:local",
                "metadata": {"runner_backend": "docker-container"},
            }
        )
