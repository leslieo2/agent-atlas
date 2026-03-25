from __future__ import annotations

from uuid import UUID

from app.infrastructure.repositories.common import state, to_uuid
from app.modules.adapters.domain.models import AdapterDescriptor
from app.modules.artifacts.domain.models import ArtifactMetadata


class StateArtifactRepository:
    def get(self, artifact_id: str | UUID) -> ArtifactMetadata | None:
        with state.lock:
            return state.artifacts.get(to_uuid(artifact_id))

    def save(self, artifact: ArtifactMetadata) -> None:
        state.save_artifact(artifact)


class StateAdapterCatalog:
    def list_adapters(self) -> list[AdapterDescriptor]:
        return list(state.adapters)


__all__ = ["StateAdapterCatalog", "StateArtifactRepository"]
