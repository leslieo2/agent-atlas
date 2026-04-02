from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from agent_atlas_contracts.runtime import (
    ExecutionReferenceMetadata as ContractExecutionReferenceMetadata,
)
from agent_atlas_contracts.runtime import (
    TraceTelemetryMetadata as ContractTraceTelemetryMetadata,
)
from pydantic import BaseModel, Field

from app.modules.shared.domain.enums import PolicyEffect, ScoringMode, StepType


def utc_now() -> datetime:
    return datetime.now(UTC)


def build_source_artifact_ref(agent_id: str, source_fingerprint: str) -> str:
    return f"source://{agent_id}@{source_fingerprint}"


class ExecutionReferenceMetadata(ContractExecutionReferenceMetadata):
    pass


def build_source_execution_reference(
    *,
    agent_id: str,
    source_fingerprint: str,
) -> ExecutionReferenceMetadata:
    return ExecutionReferenceMetadata(
        artifact_ref=build_source_artifact_ref(agent_id, source_fingerprint),
        image_ref=None,
    )


class ProvenanceMetadata(BaseModel):
    agent_family: str | None = None
    framework: str | None = None
    framework_version: str | None = None
    published_agent_snapshot: dict[str, Any] | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None
    runner_backend: str | None = None
    executor_backend: str | None = None
    trace_backend: str | None = None
    experiment_id: UUID | None = None
    dataset_version_id: UUID | None = None
    dataset_sample_id: str | None = None
    approval_policy: ApprovalPolicySnapshot | None = None
    toolset: ToolsetConfig | None = None
    evaluator: EvaluatorConfig | None = None
    executor: ExecutorConfig | None = None


class TracingMetadata(BaseModel):
    backend: str
    trace_id: str | None = None
    trace_url: str | None = None
    project_url: str | None = None


class TraceTelemetryMetadata(ContractTraceTelemetryMetadata):
    pass


class ToolPolicyRule(BaseModel):
    tool_name: str
    effect: PolicyEffect
    description: str | None = None


class ApprovalPolicySnapshot(BaseModel):
    approval_policy_id: UUID | None = None
    name: str | None = None
    tool_policies: list[ToolPolicyRule] = Field(default_factory=list)


class ModelConfig(BaseModel):
    model: str
    provider: str | None = None
    temperature: float = 0.0


class PromptConfig(BaseModel):
    prompt_template: str | None = None
    system_prompt: str | None = None
    prompt_version: str | None = None


class ToolsetConfig(BaseModel):
    tools: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluatorConfig(BaseModel):
    scoring_mode: ScoringMode = ScoringMode.EXACT_MATCH
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutorResources(BaseModel):
    cpu: str | None = None
    memory: str | None = None


class ExecutorConfig(BaseModel):
    backend: str
    runner_image: str | None = None
    timeout_seconds: int = 600
    max_steps: int = 32
    concurrency: int = 1
    resources: ExecutorResources = Field(default_factory=ExecutorResources)
    tracing_backend: str = "state"
    artifact_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


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
