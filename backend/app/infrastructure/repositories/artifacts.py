from __future__ import annotations

from uuid import UUID

from app.infrastructure.repositories.common import persistence, to_uuid
from app.modules.artifacts.domain.models import ArtifactMetadata


class StateArtifactRepository:
    def get(self, artifact_id: str | UUID) -> ArtifactMetadata | None:
        return persistence.get_artifact(to_uuid(artifact_id))

    def list(self) -> list[ArtifactMetadata]:
        return persistence.list_artifacts()

    def save(self, artifact: ArtifactMetadata) -> None:
        persistence.save_artifact(artifact)

__all__ = ["StateArtifactRepository"]
