from __future__ import annotations

from uuid import UUID

from app.core.errors import AgentLoadFailedError
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
        manifest = snapshot.get("manifest")
        entrypoint = snapshot.get("entrypoint")
        framework = provenance.framework
        if not isinstance(manifest, dict):
            raise AgentLoadFailedError(
                "published agent snapshot is missing manifest metadata",
                agent_id=payload.agent_id,
            )
        if framework is None and isinstance(manifest.get("framework"), str):
            framework = str(manifest["framework"])

        return ResolvedRunArtifact(
            framework=framework,
            entrypoint=entrypoint if isinstance(entrypoint, str) else payload.entrypoint,
            artifact_ref=provenance.artifact_ref,
            image_ref=provenance.image_ref,
            published_agent_snapshot=snapshot,
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
