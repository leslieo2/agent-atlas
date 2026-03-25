from __future__ import annotations

from uuid import UUID

from app.modules.artifacts.application.ports import ArtifactExportPort, ArtifactRepository
from app.modules.artifacts.domain.models import ArtifactExportRequest, ArtifactMetadata


class ArtifactQueries:
    def __init__(self, artifact_repository: ArtifactRepository) -> None:
        self.artifact_repository = artifact_repository

    def get_artifact(self, artifact_id: str | UUID) -> ArtifactMetadata | None:
        return self.artifact_repository.get(artifact_id)


class ArtifactCommands:
    def __init__(self, artifact_exporter: ArtifactExportPort) -> None:
        self.artifact_exporter = artifact_exporter

    def export(self, payload: ArtifactExportRequest) -> ArtifactMetadata:
        return self.artifact_exporter.export(payload)
