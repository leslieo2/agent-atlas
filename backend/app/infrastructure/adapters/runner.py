from __future__ import annotations

from uuid import UUID

from app.core.errors import AgentLoadFailedError
from app.modules.agents.domain.models import PublishedAgent
from app.modules.runs.application.ports import (
    ArtifactResolverPort,
    PublishedRunRuntimePort,
)
from app.modules.runs.application.results import PublishedRunExecutionResult
from app.modules.runs.domain.models import ResolvedRunArtifact, RunSpec


class PublishedArtifactResolver:
    def resolve(self, payload: RunSpec) -> ResolvedRunArtifact:
        provenance = payload.provenance
        if provenance is None or provenance.published_agent_snapshot is None:
            raise AgentLoadFailedError(
                "run payload is missing a published agent snapshot",
                agent_id=payload.agent_id,
            )

        snapshot = provenance.published_agent_snapshot
        try:
            published_agent = PublishedAgent.model_validate(snapshot)
        except Exception as exc:
            raise AgentLoadFailedError(
                "published agent snapshot is missing manifest metadata",
                agent_id=payload.agent_id,
            ) from exc

        manifest = snapshot.get("manifest")
        if not isinstance(manifest, dict):
            raise AgentLoadFailedError(
                "published agent snapshot is missing manifest metadata",
                agent_id=payload.agent_id,
            )
        runtime_artifact = published_agent.effective_runtime_artifact()
        framework = provenance.framework or runtime_artifact.framework
        entrypoint = runtime_artifact.entrypoint or published_agent.entrypoint or payload.entrypoint
        artifact_ref = provenance.artifact_ref or runtime_artifact.artifact_ref
        image_ref = provenance.image_ref or runtime_artifact.image_ref
        source_fingerprint = runtime_artifact.source_fingerprint
        if artifact_ref is None and image_ref is None:
            raise AgentLoadFailedError(
                "published agent snapshot is missing runtime artifact metadata",
                agent_id=payload.agent_id,
                framework=framework or "unknown",
            )

        return ResolvedRunArtifact(
            framework=framework,
            entrypoint=entrypoint,
            source_fingerprint=source_fingerprint,
            artifact_ref=artifact_ref,
            image_ref=image_ref,
            published_agent_snapshot=published_agent.to_snapshot(),
        )


class LegacyPassthroughRunner:
    def __init__(
        self,
        artifact_resolver: ArtifactResolverPort,
        published_runtime: PublishedRunRuntimePort,
    ) -> None:
        self.artifact_resolver = artifact_resolver
        self.published_runtime = published_runtime

    def execute(self, run_id: UUID, payload: RunSpec) -> PublishedRunExecutionResult:
        self.artifact_resolver.resolve(payload)
        return self.published_runtime.execute_published(run_id, payload)
