from __future__ import annotations

from uuid import UUID

from app.db.persistence import StatePersistence
from app.infrastructure.repositories.common import resolve_state_persistence, to_uuid
from app.modules.exports.domain.models import ArtifactMetadata


class StateExportRepository:
    def __init__(self, persistence: StatePersistence | None = None) -> None:
        self._persistence = resolve_state_persistence(persistence)

    def get(self, artifact_id: str | UUID) -> ArtifactMetadata | None:
        return self._persistence.get_artifact(to_uuid(artifact_id))

    def list(self) -> list[ArtifactMetadata]:
        return self._persistence.list_artifacts()

    def save(self, artifact: ArtifactMetadata) -> None:
        self._persistence.save_artifact(artifact)


__all__ = ["StateExportRepository"]
