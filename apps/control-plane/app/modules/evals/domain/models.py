from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.modules.shared.domain.enums import RunStatus
from app.modules.shared.domain.models import ObservabilityMetadata


def utc_now() -> datetime:
    return datetime.now(UTC)


class EvalJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScoringMode(str, Enum):
    EXACT_MATCH = "exact_match"
    CONTAINS = "contains"


class SampleJudgement(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    UNSCORED = "unscored"
    RUNTIME_ERROR = "runtime_error"


class CurationStatus(str, Enum):
    INCLUDE = "include"
    EXCLUDE = "exclude"
    REVIEW = "review"


class CompareOutcome(str, Enum):
    IMPROVED = "improved"
    REGRESSED = "regressed"
    UNCHANGED_PASS = "unchanged_pass"  # nosec B105 - compare label, not a credential
    UNCHANGED_FAIL = "unchanged_fail"
    CANDIDATE_ONLY = "candidate_only"
    BASELINE_ONLY = "baseline_only"


class EvalJobCreateInput(BaseModel):
    agent_id: str
    dataset: str
    project: str
    tags: list[str] = Field(default_factory=list)
    scoring_mode: ScoringMode = ScoringMode.EXACT_MATCH


class EvalJobRecord(BaseModel):
    eval_job_id: UUID = Field(default_factory=uuid4)
    agent_id: str
    dataset: str
    project: str
    tags: list[str] = Field(default_factory=list)
    scoring_mode: ScoringMode
    status: EvalJobStatus = EvalJobStatus.QUEUED
    sample_count: int = 0
    scored_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    unscored_count: int = 0
    runtime_error_count: int = 0
    pass_rate: float = 0.0
    failure_distribution: dict[str, int] = Field(default_factory=dict)
    observability: ObservabilityMetadata | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class EvalDatasetSample(BaseModel):
    sample_id: str
    input: str
    expected: str | None = None
    tags: list[str] = Field(default_factory=list)
    slice: str | None = None
    source: str | None = None
    metadata: dict[str, Any] | None = None
    export_eligible: bool | None = None


class EvalDataset(BaseModel):
    name: str
    samples: list[EvalDatasetSample] = Field(default_factory=list)


class EvalSampleResult(BaseModel):
    eval_job_id: UUID
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
    runner_backend: str | None = None
    framework: str | None = None
    latency_ms: int | None = None
    tool_calls: int | None = None
    prompt_version: str | None = None
    image_digest: str | None = None


class EvalSamplePatchInput(BaseModel):
    curation_status: CurationStatus | None = None
    curation_note: str | None = None
    export_eligible: bool | None = None


class CandidateRunSummary(BaseModel):
    run_id: UUID
    actual: str | None = None
    trace_url: str | None = None


class EvalCompareSample(BaseModel):
    dataset_sample_id: str
    baseline_judgement: SampleJudgement | None = None
    candidate_judgement: SampleJudgement | None = None
    compare_outcome: CompareOutcome
    error_code: str | None = None
    slice: str | None = None
    tags: list[str] = Field(default_factory=list)
    candidate_run_summary: CandidateRunSummary | None = None


class EvalCompareResult(BaseModel):
    baseline_eval_job_id: UUID
    candidate_eval_job_id: UUID
    dataset: str
    distribution: dict[str, int] = Field(default_factory=dict)
    samples: list[EvalCompareSample] = Field(default_factory=list)


class EvalRunState(BaseModel):
    run_id: UUID
    dataset_sample_id: str
    status: RunStatus
    actual: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    termination_reason: str | None = None
    trace_url: str | None = None
    published_agent_snapshot: dict[str, Any] | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None
    runner_backend: str | None = None
    framework: str | None = None
    latency_ms: int | None = None
    tool_calls: int | None = None
