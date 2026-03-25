from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.modules.shared.domain.enums import ArtifactFormat


class ArtifactExportRequest(BaseModel):
    run_ids: list[UUID]
    format: ArtifactFormat = ArtifactFormat.JSONL


class ArtifactMetadata(BaseModel):
    artifact_id: UUID = Field(default_factory=uuid4)
    format: ArtifactFormat
    run_ids: list[UUID]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    path: str
    size_bytes: int
