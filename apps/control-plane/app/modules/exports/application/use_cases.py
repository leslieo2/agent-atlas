from __future__ import annotations

from uuid import UUID

from app.modules.exports.application.ports import ExportPort, ExportRepository
from app.modules.exports.domain.models import ArtifactExportRequest, ArtifactMetadata


class ExportQueries:
    def __init__(self, export_repository: ExportRepository) -> None:
        self.export_repository = export_repository

    def get_export(self, artifact_id: str | UUID) -> ArtifactMetadata | None:
        return self.export_repository.get(artifact_id)

    def list_exports(self) -> list[ArtifactMetadata]:
        return self.export_repository.list()


class ExportCommands:
    def __init__(self, exporter: ExportPort) -> None:
        self.exporter = exporter

    def export(self, payload: ArtifactExportRequest) -> ArtifactMetadata:
        return self.exporter.export(payload)
