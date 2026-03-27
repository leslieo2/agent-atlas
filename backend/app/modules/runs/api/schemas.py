from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.runs.domain.models import RunCreateInput, RunRecord, TrajectoryStep
from app.modules.shared.domain.enums import AdapterKind, RunStatus, StepType


class RunCreateRequest(BaseModel):
    project: str
    dataset: str | None = None
    agent_id: str
    input_summary: str
    prompt: str
    tags: list[str] = Field(default_factory=list)
    project_metadata: dict[str, object] = Field(default_factory=dict)
    eval_job_id: UUID | None = None
    dataset_sample_id: str | None = None

    def to_domain(self) -> RunCreateInput:
        return RunCreateInput.model_validate(self.model_dump())


class RunResponse(BaseModel):
    run_id: UUID
    input_summary: str
    status: RunStatus
    latency_ms: int
    token_cost: int
    tool_calls: int
    project: str
    dataset: str | None = None
    eval_job_id: UUID | None = None
    dataset_sample_id: str | None = None
    agent_id: str
    model: str
    entrypoint: str | None = None
    agent_type: AdapterKind
    tags: list[str]
    created_at: datetime
    project_metadata: dict[str, object]
    artifact_ref: str | None = None
    execution_backend: str | None = None
    container_image: str | None = None
    resolved_model: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    termination_reason: str | None = None

    @classmethod
    def from_domain(cls, run: RunRecord) -> RunResponse:
        return cls.model_validate(run.model_dump())


class TerminateRunResponse(BaseModel):
    run_id: UUID
    terminated: bool
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
