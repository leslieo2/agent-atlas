from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.modules.artifacts.domain.models import (
    ArtifactExportRequest as DomainArtifactExportRequest,
)
from app.modules.artifacts.domain.models import ArtifactMetadata
from app.modules.shared.domain.enums import ArtifactFormat


class ArtifactExportRequest(BaseModel):
    run_ids: list[UUID]
    format: ArtifactFormat = ArtifactFormat.JSONL

    def to_domain(self) -> DomainArtifactExportRequest:
        return DomainArtifactExportRequest.model_validate(self.model_dump())


class ArtifactMetadataResponse(BaseModel):
    artifact_id: UUID
    format: ArtifactFormat
    run_ids: list[UUID]
    created_at: datetime
    path: str
    size_bytes: int

    @classmethod
    def from_domain(cls, artifact: ArtifactMetadata) -> ArtifactMetadataResponse:
        return cls.model_validate(artifact.model_dump())
