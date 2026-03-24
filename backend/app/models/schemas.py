from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class StepType(str, Enum):
    LLM = "llm"
    TOOL = "tool"
    PLANNER = "planner"
    MEMORY = "memory"


class EvalStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ArtifactFormat(str, Enum):
    JSONL = "jsonl"
    PARQUET = "parquet"


class AdapterKind(str, Enum):
    OPENAI_AGENTS = "openai-agents-sdk"
    LANGCHAIN = "langchain"
    MCP = "mcp"


class AdapterDescriptor(BaseModel):
    kind: AdapterKind
    name: str
    runtime_version: str
    notes: str
    supports_replay: bool = True
    supports_eval: bool = True


class RunCreateRequest(BaseModel):
    project: str
    dataset: str
    model: str
    agent_type: AdapterKind
    input_summary: str
    prompt: str
    tags: list[str] = Field(default_factory=list)
    tool_config: dict[str, Any] = Field(default_factory=dict)
    project_metadata: dict[str, Any] = Field(default_factory=dict)


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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    project_metadata: dict[str, Any] = Field(default_factory=dict)
    artifact_ref: str | None = None


class TrajectoryStep(BaseModel):
    id: str
    run_id: UUID
    step_type: StepType
    prompt: str
    output: str
    model: str
    temperature: float = 0.0
    latency_ms: int = 0
    token_usage: int = 0
    success: bool = True
    tool_name: str | None = None
    started_at: datetime = Field(default_factory=datetime.utcnow)


class TraceIngestEvent(BaseModel):
    run_id: UUID
    span_id: str
    parent_span_id: str | None = None
    step_type: StepType = StepType.LLM
    name: str
    input: dict[str, Any]
    output: dict[str, Any] = Field(default_factory=dict)
    tool_name: str | None = None
    latency_ms: int = 0
    token_usage: int = 0
    image_digest: str | None = None
    prompt_version: str | None = None


class TraceSpan(BaseModel):
    run_id: UUID
    span_id: str
    parent_span_id: str | None
    step_type: StepType
    input: dict[str, Any]
    output: dict[str, Any]
    tool_name: str | None = None
    latency_ms: int
    token_usage: int
    image_digest: str | None = None
    prompt_version: str | None = None
    received_at: datetime = Field(default_factory=datetime.utcnow)


class ReplayRequest(BaseModel):
    run_id: UUID
    step_id: str
    edited_prompt: str | None = None
    model: str | None = None
    tool_overrides: dict[str, Any] = Field(default_factory=dict)
    rationale: str | None = None


class ReplayResult(BaseModel):
    replay_id: UUID
    run_id: UUID
    step_id: str
    baseline_output: str
    replay_output: str
    diff: str
    updated_prompt: str | None
    model: str
    temperature: float = 0.0
    started_at: datetime = Field(default_factory=datetime.utcnow)


class EvalJobCreate(BaseModel):
    run_ids: list[UUID]
    dataset: str
    evaluators: list[str] = Field(default_factory=lambda: ["rule", "llm_judge", "tool_correctness"])


class EvalResult(BaseModel):
    sample_id: str
    run_id: UUID
    input: str
    status: str
    score: float
    reason: str | None = None


class EvalJob(BaseModel):
    job_id: UUID = Field(default_factory=uuid4)
    run_ids: list[UUID]
    dataset: str
    status: EvalStatus = EvalStatus.QUEUED
    results: list[EvalResult] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DatasetSample(BaseModel):
    sample_id: str
    input: str
    expected: str | None = None
    tags: list[str] = Field(default_factory=list)


class Dataset(BaseModel):
    name: str
    rows: list[DatasetSample]


class DatasetCreate(BaseModel):
    name: str
    rows: list[DatasetSample]


class ArtifactExportRequest(BaseModel):
    run_ids: list[UUID]
    format: ArtifactFormat = ArtifactFormat.JSONL


class ArtifactMetadata(BaseModel):
    artifact_id: UUID = Field(default_factory=uuid4)
    format: ArtifactFormat
    run_ids: list[UUID]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    path: str
    size_bytes: int
