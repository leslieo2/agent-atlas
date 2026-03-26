from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.runs.domain.models import RunRecord, RunSpec, TrajectoryStep
from app.modules.shared.domain.enums import AdapterKind, RunStatus, StepType


class RunCreateRequest(BaseModel):
    project: str
    dataset: str | None = None
    model: str
    agent_type: AdapterKind
    input_summary: str
    prompt: str
    tags: list[str] = Field(default_factory=list)
    tool_config: dict[str, object] = Field(default_factory=dict)
    project_metadata: dict[str, object] = Field(default_factory=dict)

    def to_domain(self) -> RunSpec:
        return RunSpec.model_validate(self.model_dump())


class RunResponse(BaseModel):
    run_id: UUID
    input_summary: str
    status: RunStatus
    latency_ms: int
    token_cost: int
    tool_calls: int
    project: str
    dataset: str | None = None
    model: str
    agent_type: AdapterKind
    tags: list[str]
    created_at: datetime
    project_metadata: dict[str, object]
    artifact_ref: str | None = None
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
    model: str
    temperature: float
    latency_ms: int
    token_usage: int
    success: bool
    tool_name: str | None = None
    started_at: datetime

    @classmethod
    def from_domain(cls, step: TrajectoryStep) -> TrajectoryStepResponse:
        return cls.model_validate(step.model_dump())
