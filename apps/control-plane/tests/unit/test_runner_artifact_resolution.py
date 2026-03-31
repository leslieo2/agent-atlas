from __future__ import annotations

from uuid import uuid4

import pytest
from agent_atlas_contracts.execution import ExecutionArtifact, ExecutionHandoff
from app.core.errors import AgentLoadFailedError
from app.execution.adapters import (
    LocalProcessRunner,
    PublishedArtifactResolver,
    execution_handoff_from_run_spec,
    runner_run_spec_from_handoff,
)
from app.execution.contracts import ExecutionRunSpec
from app.modules.agents.domain.models import AgentManifest, PublishedAgent
from app.modules.shared.domain.enums import AdapterKind
from app.modules.shared.domain.models import ProvenanceMetadata, build_source_runtime_artifact


def test_published_artifact_resolver_accepts_source_backed_handoff() -> None:
    published_agent = PublishedAgent(
        manifest=AgentManifest(
            agent_id="basic",
            name="Basic",
            description="Basic agent",
            framework=AdapterKind.OPENAI_AGENTS.value,
            default_model="gpt-5.4-mini",
            tags=["example"],
        ),
        entrypoint="app.agent_plugins.basic:build_agent",
        runtime_artifact=build_source_runtime_artifact(
            agent_id="basic",
            source_fingerprint="fingerprint-123",
            framework=AdapterKind.OPENAI_AGENTS.value,
            entrypoint="app.agent_plugins.basic:build_agent",
        ),
    )
    payload = ExecutionRunSpec(
        project="resolver-test",
        dataset=None,
        agent_id="basic",
        model="gpt-5.4-mini",
        entrypoint="app.agent_plugins.basic:build_agent",
        agent_type=AdapterKind.OPENAI_AGENTS,
        input_summary="resolve handoff",
        prompt="Resolve the artifact handoff.",
        provenance=ProvenanceMetadata(
            framework=AdapterKind.OPENAI_AGENTS.value,
            published_agent_snapshot=published_agent.to_snapshot(),
            artifact_ref="source://basic@fingerprint-123",
        ),
    )

    resolved = PublishedArtifactResolver().resolve(payload)

    assert resolved.framework == AdapterKind.OPENAI_AGENTS.value
    assert resolved.entrypoint == "app.agent_plugins.basic:build_agent"
    assert resolved.source_fingerprint == "fingerprint-123"
    assert resolved.artifact_ref == "source://basic@fingerprint-123"


def test_published_artifact_resolver_rejects_missing_runtime_handoff() -> None:
    payload = ExecutionRunSpec(
        project="resolver-test",
        dataset=None,
        agent_id="basic",
        model="gpt-5.4-mini",
        entrypoint="app.agent_plugins.basic:build_agent",
        agent_type=AdapterKind.OPENAI_AGENTS,
        input_summary="resolve handoff",
        prompt="Resolve the artifact handoff.",
        provenance=ProvenanceMetadata(
            framework=AdapterKind.OPENAI_AGENTS.value,
            published_agent_snapshot={"entrypoint": "app.agent_plugins.basic:build_agent"},
        ),
    )

    with pytest.raises(AgentLoadFailedError, match="missing manifest metadata"):
        PublishedArtifactResolver().resolve(payload)


def test_runner_execution_handoff_builds_from_resolved_artifact() -> None:
    run_id = uuid4()
    payload = ExecutionRunSpec(
        project="resolver-test",
        dataset="resolver-dataset",
        agent_id="basic",
        model="gpt-5.4-mini",
        entrypoint="app.agent_plugins.basic:build_agent",
        agent_type=AdapterKind.OPENAI_AGENTS,
        input_summary="resolve handoff",
        prompt="Resolve the artifact handoff.",
        tags=["phase4"],
        project_metadata={"branch": "main"},
        provenance=ProvenanceMetadata(trace_backend="phoenix"),
    )

    artifact = ExecutionArtifact(
        framework=AdapterKind.OPENAI_AGENTS.value,
        entrypoint="app.agent_plugins.basic:build_agent",
        source_fingerprint="fingerprint-123",
        artifact_ref="source://basic@fingerprint-123",
        image_ref=None,
        published_agent_snapshot={
            "manifest": {
                "agent_id": "basic",
                "name": "Basic",
                "description": "Basic agent",
                "framework": "openai-agents-sdk",
                "default_model": "gpt-5.4-mini",
                "tags": ["example"],
            },
            "entrypoint": "app.agent_plugins.basic:build_agent",
            "published_at": "2026-03-20T09:00:00Z",
            "runtime_artifact": {
                "build_status": "ready",
                "source_fingerprint": "fingerprint-123",
                "framework": AdapterKind.OPENAI_AGENTS.value,
                "entrypoint": "app.agent_plugins.basic:build_agent",
                "artifact_ref": "source://basic@fingerprint-123",
                "image_ref": None,
            },
        },
    )

    handoff = execution_handoff_from_run_spec(
        run_id=run_id,
        payload=payload,
        artifact=artifact,
        runner_backend="local-process",
        attempt=2,
        attempt_id=uuid4(),
    )

    assert handoff.run_id == run_id
    assert handoff.runner_backend == "local-process"
    assert handoff.attempt == 2
    assert handoff.attempt_id is not None
    assert handoff.framework == AdapterKind.OPENAI_AGENTS.value
    assert handoff.artifact_ref == "source://basic@fingerprint-123"
    assert handoff.project_metadata == {"branch": "main"}
    assert handoff.executor_config["backend"] == "local-runner"
    assert runner_run_spec_from_handoff(handoff).agent_type == AdapterKind.OPENAI_AGENTS.value


def test_local_process_runner_stamps_runner_backend() -> None:
    run_id = uuid4()
    handoff = ExecutionHandoff(
        run_id=run_id,
        runner_backend="local-process",
        project="resolver-test",
        dataset=None,
        attempt=3,
        attempt_id=uuid4(),
        agent_id="basic",
        model="gpt-5.4-mini",
        entrypoint="app.agent_plugins.basic:build_agent",
        agent_type=AdapterKind.OPENAI_AGENTS.value,
        prompt="Resolve the artifact handoff.",
        framework=AdapterKind.OPENAI_AGENTS.value,
        artifact_ref="source://basic@fingerprint-123",
        image_ref=None,
        published_agent_snapshot={
            "manifest": {
                "agent_id": "basic",
                "name": "Basic",
                "description": "Basic agent",
                "framework": "openai-agents-sdk",
                "default_model": "gpt-5.4-mini",
                "tags": [],
            },
            "entrypoint": "app.agent_plugins.basic:build_agent",
            "published_at": "2026-03-20T09:00:00Z",
            "runtime_artifact": {
                "build_status": "ready",
                "source_fingerprint": "fingerprint-123",
                "framework": AdapterKind.OPENAI_AGENTS.value,
                "entrypoint": "app.agent_plugins.basic:build_agent",
                "artifact_ref": "source://basic@fingerprint-123",
                "image_ref": None,
            },
        },
    )

    result = LocalProcessRunner().execute(handoff)

    assert result.runner_backend == "local-process"
    assert result.artifact_ref == "source://basic@fingerprint-123"
    assert result.execution.runtime_result.output
    assert result.execution.runtime_result.provider in {"mock", "openai-agents-sdk"}
    assert result.execution.terminal_result is not None
    assert result.execution.terminal_result.attempt == 3
    assert result.execution.terminal_result.attempt_id == handoff.attempt_id
