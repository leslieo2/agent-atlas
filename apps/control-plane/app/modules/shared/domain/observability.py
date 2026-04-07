from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from agent_atlas_contracts.runtime import (
    TraceTelemetryMetadata as ContractTraceTelemetryMetadata,
)
from pydantic import BaseModel, Field

from app.modules.shared.domain.enums import StepType


def utc_now() -> datetime:
    return datetime.now(UTC)


class TracingMetadata(BaseModel):
    backend: str
    trace_id: str | None = None
    trace_url: str | None = None
    project_url: str | None = None


class TraceTelemetryMetadata(ContractTraceTelemetryMetadata):
    pass


class TracePointer(BaseModel):
    backend: str
    trace_id: str | None = None
    trace_url: str | None = None
    project_url: str | None = None


class TrajectoryStepRecord(BaseModel):
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


class RunLineage(BaseModel):
    experiment_id: UUID | None = None
    dataset_name: str | None = None
    dataset_version_id: UUID | None = None
    dataset_sample_id: str | None = None
    export_batch_ids: list[UUID] = Field(default_factory=list)
