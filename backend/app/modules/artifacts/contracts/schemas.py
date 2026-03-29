from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.modules.artifacts.domain.models import (
    ArtifactExportRequest as DomainArtifactExportRequest,
)
from app.modules.artifacts.domain.models import ArtifactMetadata
from app.modules.shared.domain.enums import (
    ArtifactFormat,
    CompareOutcome,
    CurationStatus,
    SampleJudgement,
)


class ExportCreateRequest(BaseModel):
    experiment_id: UUID | None = None
    baseline_experiment_id: UUID | None = None
    candidate_experiment_id: UUID | None = None
    dataset_sample_ids: list[str] | None = None
    judgements: list[SampleJudgement] | None = None
    error_codes: list[str] | None = None
    compare_outcomes: list[CompareOutcome] | None = None
    tags: list[str] | None = None
    slices: list[str] | None = None
    curation_statuses: list[CurationStatus] | None = None
    export_eligible: bool | None = None
    format: ArtifactFormat = ArtifactFormat.JSONL

    def to_domain(self) -> DomainArtifactExportRequest:
        return DomainArtifactExportRequest.model_validate(self.model_dump(mode="json"))


class ExportMetadataResponse(BaseModel):
    export_id: UUID
    format: ArtifactFormat
    created_at: datetime
    path: str
    size_bytes: int
    row_count: int
    source_experiment_id: UUID | None = None
    baseline_experiment_id: UUID | None = None
    candidate_experiment_id: UUID | None = None
    filters_summary: dict[str, object]

    @classmethod
    def from_domain(cls, artifact: ArtifactMetadata) -> ExportMetadataResponse:
        payload = artifact.model_dump(mode="json")
        payload["export_id"] = payload.pop("artifact_id")
        return cls.model_validate(payload)
