from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.artifacts.domain.models import (
    ArtifactExportRequest,
    ArtifactMetadata,
)


class ArtifactRepository(Protocol):
    def get(self, artifact_id: str | UUID) -> ArtifactMetadata | None: ...

    def list(self) -> list[ArtifactMetadata]: ...

    def save(self, artifact: ArtifactMetadata) -> None: ...


class ArtifactExportPort(Protocol):
    def export(self, payload: ArtifactExportRequest) -> ArtifactMetadata: ...
