from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.modules.shared.domain.enums import ArtifactFormat


class ArtifactExportRequest(BaseModel):
    run_ids: list[UUID]
    format: ArtifactFormat = ArtifactFormat.JSONL


def utc_now() -> datetime:
    return datetime.now(UTC)


class ArtifactMetadata(BaseModel):
    artifact_id: UUID = Field(default_factory=uuid4)
    format: ArtifactFormat
    run_ids: list[UUID]
    created_at: datetime = Field(default_factory=utc_now)
    path: str
    size_bytes: int
