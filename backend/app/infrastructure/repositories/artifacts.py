from __future__ import annotations

from uuid import UUID

from app.infrastructure.repositories.common import ADAPTER_CATALOG, persistence, to_uuid
from app.modules.adapters.domain.models import AdapterDescriptor
from app.modules.artifacts.domain.models import ArtifactMetadata


class StateArtifactRepository:
    def get(self, artifact_id: str | UUID) -> ArtifactMetadata | None:
        return persistence.get_artifact(to_uuid(artifact_id))

    def list(self) -> list[ArtifactMetadata]:
        return persistence.list_artifacts()

    def save(self, artifact: ArtifactMetadata) -> None:
        persistence.save_artifact(artifact)


class StateAdapterCatalog:
    def list_adapters(self) -> list[AdapterDescriptor]:
        return list(ADAPTER_CATALOG)


__all__ = ["StateAdapterCatalog", "StateArtifactRepository"]
