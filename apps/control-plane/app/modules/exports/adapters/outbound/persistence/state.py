from __future__ import annotations

from typing import cast
from uuid import UUID

from app.db.persistence import StatePersistence
from app.infrastructure.repositories.common import persistence, to_uuid
from app.modules.exports.domain.models import ArtifactMetadata

state_persistence = cast(StatePersistence, persistence)


class StateExportRepository:
    def get(self, artifact_id: str | UUID) -> ArtifactMetadata | None:
        return state_persistence.get_artifact(to_uuid(artifact_id))

    def list(self) -> list[ArtifactMetadata]:
        return state_persistence.list_artifacts()

    def save(self, artifact: ArtifactMetadata) -> None:
        state_persistence.save_artifact(artifact)


__all__ = ["StateExportRepository"]
