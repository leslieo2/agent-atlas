from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from app.modules.shared.domain.enums import (
    CompareOutcome,
    CurationStatus,
    RunStatus,
    SampleJudgement,
)
from app.modules.shared.domain.models import (
    ApprovalPolicySnapshot,
    EvaluatorConfig,
    ExecutorConfig,
    ModelConfig,
    PromptConfig,
    ToolsetConfig,
    TracingMetadata,
)
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class ExperimentStatus(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExperimentSpec(BaseModel):
    dataset_version_id: UUID
    published_agent_id: str
    model_settings: ModelConfig
    prompt_config: PromptConfig = Field(default_factory=PromptConfig)
    toolset_config: ToolsetConfig = Field(default_factory=ToolsetConfig)
    evaluator_config: EvaluatorConfig = Field(default_factory=EvaluatorConfig)
    executor_config: ExecutorConfig
    approval_policy_id: UUID | None = None
    approval_policy: ApprovalPolicySnapshot | None = None
    tags: list[str] = Field(default_factory=list)


class ExperimentCreateInput(BaseModel):
    name: str
    spec: ExperimentSpec


class ExperimentRecord(BaseModel):
    experiment_id: UUID = Field(default_factory=uuid4)
    name: str
    dataset_name: str
    dataset_version_id: UUID
    published_agent_id: str
    status: ExperimentStatus = ExperimentStatus.DRAFT
    tags: list[str] = Field(default_factory=list)
    spec: ExperimentSpec
    sample_count: int = 0
    completed_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    unscored_count: int = 0
    runtime_error_count: int = 0
    pass_rate: float = 0.0
    failure_distribution: dict[str, int] = Field(default_factory=dict)
    tracing: TracingMetadata | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class RunEvaluationRecord(BaseModel):
    experiment_id: UUID
    dataset_version_id: UUID
    dataset_sample_id: str
    run_id: UUID
    judgement: SampleJudgement
    input: str
    expected: str | None = None
    actual: str | None = None
    failure_reason: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    trace_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    slice: str | None = None
    source: str | None = None
    metadata: dict[str, Any] | None = None
    export_eligible: bool | None = None
    curation_status: CurationStatus = CurationStatus.REVIEW
    curation_note: str | None = None
    published_agent_snapshot: dict[str, Any] | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None
    executor_backend: str | None = None
    framework: str | None = None
    latency_ms: int | None = None
    tool_calls: int | None = None
    prompt_version: str | None = None
    image_digest: str | None = None
    run_status: RunStatus = RunStatus.QUEUED


class RunEvaluationPatchInput(BaseModel):
    curation_status: CurationStatus | None = None
    curation_note: str | None = None
    export_eligible: bool | None = None


class CandidateRunSummary(BaseModel):
    run_id: UUID
    actual: str | None = None
    trace_url: str | None = None


class ExperimentCompareSample(BaseModel):
    dataset_sample_id: str
    baseline_judgement: SampleJudgement | None = None
    candidate_judgement: SampleJudgement | None = None
    compare_outcome: CompareOutcome
    error_code: str | None = None
    slice: str | None = None
    tags: list[str] = Field(default_factory=list)
    candidate_run_summary: CandidateRunSummary | None = None


class ExperimentCompareResult(BaseModel):
    baseline_experiment_id: UUID
    candidate_experiment_id: UUID
    dataset_version_id: UUID
    distribution: dict[str, int] = Field(default_factory=dict)
    samples: list[ExperimentCompareSample] = Field(default_factory=list)


class ExperimentRunDetail(BaseModel):
    run_id: UUID
    experiment_id: UUID
    dataset_sample_id: str
    input: str
    expected: str | None = None
    actual: str | None = None
    run_status: RunStatus
    judgement: SampleJudgement | None = None
    compare_outcome: CompareOutcome | None = None
    failure_reason: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    tags: list[str] = Field(default_factory=list)
    slice: str | None = None
    source: str | None = None
    export_eligible: bool | None = None
    curation_status: CurationStatus = CurationStatus.REVIEW
    curation_note: str | None = None
    published_agent_snapshot: dict[str, Any] | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None
    executor_backend: str | None = None
    latency_ms: int | None = None
    tool_calls: int | None = None
    trace_url: str | None = None
