from __future__ import annotations

from uuid import uuid4

import pytest
from app.core.errors import AgentLoadFailedError
from app.infrastructure.adapters.runner import LocalProcessRunner, PublishedArtifactResolver
from app.modules.agents.domain.models import AgentManifest, PublishedAgent
from app.modules.runs.application.results import PublishedRunExecutionResult
from app.modules.runs.domain.models import (
    ResolvedRunArtifact,
    RunnerExecutionHandoff,
    RunSpec,
    RuntimeExecutionResult,
)
from app.modules.shared.domain.enums import AdapterKind
from app.modules.shared.domain.models import ProvenanceMetadata


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
        source_fingerprint="fingerprint-123",
    )
    payload = RunSpec(
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


def test_published_artifact_resolver_backfills_legacy_snapshot_runtime_artifact() -> None:
    payload = RunSpec(
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
            },
        ),
    )

    resolved = PublishedArtifactResolver().resolve(payload)

    assert resolved.artifact_ref is not None
    assert resolved.artifact_ref.startswith("source://basic@")
    assert resolved.published_agent_snapshot["runtime_artifact"]["build_status"] == "ready"


def test_published_artifact_resolver_rejects_missing_runtime_handoff() -> None:
    payload = RunSpec(
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
    payload = RunSpec(
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
        provenance=ProvenanceMetadata(trace_backend="atlas-state"),
    )

    artifact = ResolvedRunArtifact(
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
        },
    )

    handoff = RunnerExecutionHandoff.from_spec(
        run_id=run_id,
        payload=payload,
        artifact=artifact,
        runner_backend="local-process",
    )

    assert handoff.run_id == run_id
    assert handoff.runner_backend == "local-process"
    assert handoff.framework == AdapterKind.OPENAI_AGENTS.value
    assert handoff.artifact_ref == "source://basic@fingerprint-123"
    assert handoff.project_metadata == {"branch": "main"}
    assert handoff.to_run_spec().provenance.runner_backend == "local-process"


def test_local_process_runner_stamps_runner_backend() -> None:
    run_id = uuid4()

    class StubPublishedRuntime:
        def execute_published(self, *_args, **_kwargs):
            return PublishedRunExecutionResult(
                runtime_result=RuntimeExecutionResult(
                    output="ok",
                    latency_ms=5,
                    token_usage=8,
                    provider="openai-agents-sdk",
                )
            )

    handoff = RunnerExecutionHandoff(
        run_id=run_id,
        runner_backend="local-process",
        project="resolver-test",
        dataset=None,
        agent_id="basic",
        model="gpt-5.4-mini",
        entrypoint="app.agent_plugins.basic:build_agent",
        agent_type=AdapterKind.OPENAI_AGENTS,
        input_summary="resolve handoff",
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
        },
    )

    result = LocalProcessRunner(published_runtime=StubPublishedRuntime()).execute(handoff)

    assert result.runner_backend == "local-process"
    assert result.artifact_ref == "source://basic@fingerprint-123"
    assert result.execution.runtime_result.output == "ok"
