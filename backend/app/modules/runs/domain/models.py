from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.modules.shared.domain.enums import AdapterKind, RunStatus, StepType


class RunSpec(BaseModel):
    project: str
    dataset: str
    model: str
    agent_type: AdapterKind
    input_summary: str
    prompt: str
    tags: list[str] = Field(default_factory=list)
    tool_config: dict[str, Any] = Field(default_factory=dict)
    project_metadata: dict[str, Any] = Field(default_factory=dict)


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
    dataset: str
    model: str
    agent_type: AdapterKind
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    project_metadata: dict[str, Any] = Field(default_factory=dict)
    artifact_ref: str | None = None
    termination_reason: str | None = None


class TrajectoryStep(BaseModel):
    id: str
    run_id: UUID
    step_type: StepType
    parent_step_id: str | None = None
    prompt: str
    output: str
    model: str
    temperature: float = 0.0
    latency_ms: int = 0
    token_usage: int = 0
    success: bool = True
    tool_name: str | None = None
    started_at: datetime = Field(default_factory=utc_now)
