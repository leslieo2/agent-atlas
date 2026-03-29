from __future__ import annotations

from app.modules.agents.domain.models import PublishedAgent
from app.modules.shared.domain.models import ProvenanceMetadata, build_source_artifact_ref


class SourceArtifactBuilder:
    def build(self, published_agent: PublishedAgent) -> ProvenanceMetadata:
        return ProvenanceMetadata(
            framework=published_agent.framework,
            published_agent_snapshot=published_agent.to_snapshot(),
            artifact_ref=build_source_artifact_ref(
                published_agent.agent_id,
                published_agent.effective_source_fingerprint(),
            ),
            image_ref=None,
            runner_backend=None,
            trace_backend="atlas-state",
        )
