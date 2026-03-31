from __future__ import annotations

from uuid import uuid4

import pytest
from agent_atlas_contracts.execution import ExecutionArtifact, RunnerRunSpec
from app.core.errors import AgentLoadFailedError
from app.execution.adapters import (
    LocalProcessRunner,
    PublishedArtifactResolver,
    runner_run_spec_from_run_spec,
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


def test_runner_run_spec_builds_from_resolved_artifact() -> None:
    run_id = uuid4()
    payload = ExecutionRunSpec(
        run_id=run_id,
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
                "framework": AdapterKind.OPENAI_AGENTS.value,
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

    runner_payload = runner_run_spec_from_run_spec(
        payload=payload,
        artifact=artifact,
        runner_backend="local-process",
        attempt=2,
        attempt_id=uuid4(),
    )

    assert runner_payload.run_id == run_id
    assert runner_payload.runner_backend == "local-process"
    assert runner_payload.attempt == 2
    assert runner_payload.attempt_id is not None
    assert runner_payload.framework == AdapterKind.OPENAI_AGENTS.value
    assert runner_payload.artifact_ref == "source://basic@fingerprint-123"
    assert runner_payload.project_metadata == {"branch": "main"}
    assert runner_payload.executor_config["backend"] == "local-runner"
    assert runner_payload.agent_type == AdapterKind.OPENAI_AGENTS.value


def test_runner_run_spec_rejects_missing_artifact_metadata() -> None:
    payload = ExecutionRunSpec(
        project="resolver-test",
        dataset="resolver-dataset",
        agent_id="basic",
        model="gpt-5.4-mini",
        entrypoint="app.agent_plugins.basic:build_agent",
        agent_type=AdapterKind.OPENAI_AGENTS,
        input_summary="resolve handoff",
        prompt="Resolve the artifact handoff.",
        provenance=ProvenanceMetadata(
            framework=AdapterKind.OPENAI_AGENTS.value,
            artifact_ref="source://basic@fingerprint-123",
            published_agent_snapshot={"manifest": {"agent_id": "basic"}},
        ),
    )
    artifact = ExecutionArtifact(
        framework=AdapterKind.OPENAI_AGENTS.value,
        entrypoint=None,
        source_fingerprint="fingerprint-123",
        artifact_ref=None,
        image_ref=None,
        published_agent_snapshot={},
    )

    with pytest.raises(ValueError, match="resolved execution artifact is missing entrypoint"):
        runner_run_spec_from_run_spec(
            payload=payload,
            artifact=artifact,
            runner_backend="local-process",
        )


def test_local_process_runner_stamps_runner_backend(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_ATLAS_RUNTIME_MODE", "mock")
    monkeypatch.delenv("AGENT_ATLAS_OPENAI_API_KEY", raising=False)
    run_id = uuid4()
    payload = RunnerRunSpec(
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
                "framework": AdapterKind.OPENAI_AGENTS.value,
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

    result = LocalProcessRunner().execute(payload)

    assert result.runner_backend == "local-process"
    assert result.artifact_ref == "source://basic@fingerprint-123"
    assert result.execution.runtime_result.output
    assert result.execution.runtime_result.provider in {"mock", "openai-agents-sdk"}
    assert result.execution.terminal_result is not None
    assert result.execution.terminal_result.attempt == 3
    assert result.execution.terminal_result.attempt_id == payload.attempt_id
