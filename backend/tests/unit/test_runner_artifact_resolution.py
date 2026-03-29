from __future__ import annotations

import pytest
from app.core.errors import AgentLoadFailedError
from app.infrastructure.adapters.runner import PublishedArtifactResolver
from app.modules.agents.domain.models import AgentManifest, PublishedAgent
from app.modules.runs.domain.models import RunSpec
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
