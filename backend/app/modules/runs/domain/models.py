from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.modules.shared.domain.enums import AdapterKind, RunStatus, StepType
from app.modules.shared.domain.models import ProvenanceMetadata


class RunSpec(BaseModel):
    project: str
    dataset: str | None = None
    agent_id: str = ""
    model: str
    entrypoint: str | None = None
    agent_type: AdapterKind
    input_summary: str
    prompt: str
    tags: list[str] = Field(default_factory=list)
    project_metadata: dict[str, Any] = Field(default_factory=dict)
    eval_job_id: UUID | None = None
    dataset_sample_id: str | None = None
    provenance: ProvenanceMetadata | None = None


class RunCreateInput(BaseModel):
    project: str
    dataset: str | None = None
    agent_id: str
    input_summary: str
    prompt: str
    tags: list[str] = Field(default_factory=list)
    project_metadata: dict[str, Any] = Field(default_factory=dict)
    eval_job_id: UUID | None = None
    dataset_sample_id: str | None = None


class ExecutionMetrics(BaseModel):
    latency_ms: int = 0
    token_cost: int = 0
    tool_calls: int = 0


class RuntimeExecutionResult(BaseModel):
    output: str
    latency_ms: int
    token_usage: int
    provider: str
    execution_backend: str | None = None
    container_image: str | None = None
    resolved_model: str | None = None


class ResolvedRunArtifact(BaseModel):
    framework: str | None = None
    entrypoint: str | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None
    published_agent_snapshot: dict[str, Any]


def utc_now() -> datetime:
    return datetime.now(UTC)


class RunRecord(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    input_summary: str
    status: RunStatus = RunStatus.QUEUED
    latency_ms: int = 0
    token_cost: int = 0
    tool_calls: int = 0
    project: str
    dataset: str | None = None
    eval_job_id: UUID | None = None
    dataset_sample_id: str | None = None
    agent_id: str = ""
    model: str
    entrypoint: str | None = None
    agent_type: AdapterKind
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    project_metadata: dict[str, Any] = Field(default_factory=dict)
    artifact_ref: str | None = None
    execution_backend: str | None = None
    container_image: str | None = None
    provenance: ProvenanceMetadata | None = None
    resolved_model: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    termination_reason: str | None = None


class TrajectoryStep(BaseModel):
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
