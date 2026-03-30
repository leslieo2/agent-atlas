from __future__ import annotations

from app.modules.agents.domain.models import PublishedAgent
from app.modules.shared.domain.models import (
    ProvenanceMetadata,
    RuntimeArtifactBuildResult,
    build_source_runtime_artifact,
)


class SourceArtifactBuilder:
    def __init__(self, default_trace_backend: str = "state") -> None:
        self.default_trace_backend = default_trace_backend

    def build(self, published_agent: PublishedAgent) -> RuntimeArtifactBuildResult:
        runtime_artifact = build_source_runtime_artifact(
            agent_id=published_agent.agent_id,
            source_fingerprint=published_agent.effective_source_fingerprint(),
            framework=published_agent.framework,
            entrypoint=published_agent.entrypoint,
        )
        snapshot = published_agent.model_copy(
            update={"runtime_artifact": runtime_artifact},
            deep=True,
        ).to_snapshot()

        return RuntimeArtifactBuildResult(
            runtime_artifact=runtime_artifact,
            provenance=ProvenanceMetadata(
                framework=runtime_artifact.framework,
                published_agent_snapshot=snapshot,
                artifact_ref=runtime_artifact.artifact_ref,
                image_ref=runtime_artifact.image_ref,
                runner_backend=None,
                trace_backend=self.default_trace_backend,
            ),
        )
