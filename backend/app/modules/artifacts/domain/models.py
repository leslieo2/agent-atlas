from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.modules.shared.domain.enums import AdapterKind, ArtifactFormat, StepType
from app.modules.shared.domain.models import ProvenanceMetadata


class ArtifactExportRequest(BaseModel):
    run_ids: list[UUID]
    format: ArtifactFormat = ArtifactFormat.JSONL
    split: str = "train"


def utc_now() -> datetime:
    return datetime.now(UTC)


class ArtifactMetadata(BaseModel):
    artifact_id: UUID = Field(default_factory=uuid4)
    format: ArtifactFormat
    run_ids: list[UUID]
    created_at: datetime = Field(default_factory=utc_now)
    path: str
    size_bytes: int


class ArtifactRunView(BaseModel):
    run_id: UUID
    project: str
    dataset: str | None = None
    agent_id: str = ""
    entrypoint: str | None = None
    resolved_model: str | None = None
    agent_type: AdapterKind
    project_metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: ProvenanceMetadata | None = None


class ArtifactTrajectoryStepView(BaseModel):
    id: str
    run_id: UUID
    step_type: StepType
    parent_step_id: str | None = None
    prompt: str
    output: str
    model: str | None = None
    temperature: float = 0.0
    latency_ms: int = 0
    token_usage: int = 0
    success: bool = True
    tool_name: str | None = None
    started_at: datetime = Field(default_factory=utc_now)
