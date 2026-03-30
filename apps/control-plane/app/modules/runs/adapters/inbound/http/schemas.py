from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.runs.domain.models import RunCreateInput, RunRecord, TrajectoryStep
from app.modules.shared.domain.enums import AdapterKind, RunStatus, StepType
from app.modules.shared.domain.models import (
    ApprovalPolicySnapshot,
    ExecutorConfig,
    ProvenanceMetadata,
    RunLineage,
    ToolsetConfig,
    TracingMetadata,
    TracePointer,
)
from app.modules.shared.domain.traces import TraceSpan


class RunCreateRequest(BaseModel):
    experiment_id: UUID | None = None
    dataset_version_id: UUID | None = None
    project: str
    dataset: str | None = None
    agent_id: str
    input_summary: str
    prompt: str
    tags: list[str] = Field(default_factory=list)
    project_metadata: dict[str, object] = Field(default_factory=dict)
    dataset_sample_id: str | None = None
    executor_backend: str = "local-runner"
    executor_config: ExecutorConfig | None = None
    toolset_config: ToolsetConfig = Field(default_factory=ToolsetConfig)
    approval_policy: ApprovalPolicySnapshot | None = None

    def to_domain(self) -> RunCreateInput:
        return RunCreateInput.model_validate(self.model_dump())


class RunResponse(BaseModel):
    run_id: UUID
    attempt_id: UUID
    experiment_id: UUID | None = None
    dataset_version_id: UUID | None = None
    input_summary: str
    status: RunStatus
    latency_ms: int
    token_cost: int
    tool_calls: int
    project: str
    dataset: str | None = None
    dataset_sample_id: str | None = None
    agent_id: str
    model: str
    entrypoint: str | None = None
    agent_type: AdapterKind
    tags: list[str]
    created_at: datetime
    project_metadata: dict[str, object]
    artifact_ref: str | None = None
    image_ref: str | None = None
    executor_backend: str | None = None
    executor_submission_id: str | None = None
    attempt: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    runner_backend: str | None = None
    execution_backend: str | None = None
    container_image: str | None = None
    provenance: ProvenanceMetadata | None = None
    tracing: TracingMetadata | None = None
    trace_pointer: TracePointer | None = None
    lineage: RunLineage | None = None
    resolved_model: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    termination_reason: str | None = None
    terminal_reason: str | None = None
    last_heartbeat_at: datetime | None = None
    last_progress_at: datetime | None = None
    lease_expires_at: datetime | None = None

    @classmethod
    def from_domain(cls, run: RunRecord) -> RunResponse:
        return cls.model_validate(run.model_dump(mode="json"))


class CancelRunResponse(BaseModel):
    run_id: UUID
    cancelled: bool
    status: RunStatus
    termination_reason: str | None = None


class TrajectoryStepResponse(BaseModel):
    id: str
    run_id: UUID
    step_type: StepType
    parent_step_id: str | None = None
    prompt: str
    output: str
    model: str | None = None
    temperature: float
    latency_ms: int
    token_usage: int
    success: bool
    tool_name: str | None = None
    started_at: datetime

    @classmethod
    def from_domain(cls, step: TrajectoryStep) -> TrajectoryStepResponse:
        return cls.model_validate(step.model_dump())


class RunTraceSpanResponse(BaseModel):
    run_id: UUID
    span_id: str
    parent_span_id: str | None
    step_type: StepType
    input: dict[str, object]
    output: dict[str, object]
    tool_name: str | None = None
    latency_ms: int
    token_usage: int
    image_digest: str | None = None
    prompt_version: str | None = None
    trace_backend: str | None = None
    received_at: datetime

    @classmethod
    def from_domain(cls, span: TraceSpan) -> RunTraceSpanResponse:
        return cls.model_validate(span.model_dump())
