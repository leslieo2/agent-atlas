from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.modules.shared.domain.enums import ArtifactFormat


def utc_now() -> datetime:
    return datetime.now(UTC)


class ArtifactExportRequest(BaseModel):
    experiment_id: UUID | None = None
    baseline_experiment_id: UUID | None = None
    candidate_experiment_id: UUID | None = None
    dataset_sample_ids: list[str] | None = None
    judgements: list[str] | None = None
    error_codes: list[str] | None = None
    compare_outcomes: list[str] | None = None
    tags: list[str] | None = None
    slices: list[str] | None = None
    curation_statuses: list[str] | None = None
    export_eligible: bool | None = None
    format: ArtifactFormat = ArtifactFormat.JSONL


class ArtifactMetadata(BaseModel):
    artifact_id: UUID = Field(default_factory=uuid4)
    format: ArtifactFormat
    created_at: datetime = Field(default_factory=utc_now)
    path: str
    size_bytes: int
    row_count: int = 0
    source_experiment_id: UUID | None = None
    baseline_experiment_id: UUID | None = None
    candidate_experiment_id: UUID | None = None
    filters_summary: dict[str, Any] = Field(default_factory=dict)
