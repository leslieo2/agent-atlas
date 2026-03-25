from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.artifacts.domain.models import ArtifactExportRequest, ArtifactMetadata
from app.modules.runs.domain.models import RunRecord, TrajectoryStep


class ArtifactRepository(Protocol):
    def get(self, artifact_id: str | UUID) -> ArtifactMetadata | None: ...

    def save(self, artifact: ArtifactMetadata) -> None: ...


class ArtifactExportPort(Protocol):
    def export(self, payload: ArtifactExportRequest) -> ArtifactMetadata: ...


class TrajectoryExportSource(Protocol):
    def list_for_run(self, run_id: str | UUID) -> list[TrajectoryStep]: ...


class RunLookupSource(Protocol):
    def get(self, run_id: str | UUID) -> RunRecord | None: ...
