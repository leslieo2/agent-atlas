from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class ProducerInfo(BaseModel):
    kind: str = "runner"
    runtime: str | None = None
    framework: str | None = None
    language: str | None = None
    version: str | None = None


class EventEnvelope(BaseModel):
    schema_version: Literal["runner-event.v1"] = "runner-event.v1"
    run_id: UUID
    experiment_id: UUID | None = None
    attempt: int = 1
    attempt_id: UUID | None = None
    event_id: str
    parent_event_id: str | None = None
    sequence: int = 0
    event_type: str
    ts: datetime = Field(default_factory=utc_now)
    producer: ProducerInfo = Field(default_factory=ProducerInfo)
    payload: dict[str, Any] = Field(default_factory=dict)


class ArtifactEntry(BaseModel):
    path: str
    kind: str = "file"
    uri: str | None = None
    media_type: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactManifest(BaseModel):
    schema_version: Literal["runner-artifact-manifest.v1"] = (
        "runner-artifact-manifest.v1"
    )
    run_id: UUID
    experiment_id: UUID | None = None
    attempt: int = 1
    attempt_id: UUID | None = None
    producer: ProducerInfo = Field(default_factory=ProducerInfo)
    artifacts: list[ArtifactEntry] = Field(default_factory=list)


class TerminalMetrics(BaseModel):
    latency_ms: int = 0
    token_usage: int = 0
    tool_calls: int = 0


class TerminalResult(BaseModel):
    schema_version: Literal["runner-terminal-result.v1"] = "runner-terminal-result.v1"
    run_id: UUID
    experiment_id: UUID | None = None
    attempt: int = 1
    attempt_id: UUID | None = None
    status: str
    ts: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime = Field(default_factory=utc_now)
    reason_code: str | None = None
    reason_message: str | None = None
    exit_code: int | None = None
    output: str | None = None
    producer: ProducerInfo = Field(default_factory=ProducerInfo)
    metrics: TerminalMetrics = Field(default_factory=TerminalMetrics)


class RunnerBootstrapPaths(BaseModel):
    run_spec_path: str = "/workspace/input/run_spec.json"
    events_path: str = "/workspace/output/events.ndjson"
    terminal_result_path: str = "/workspace/output/terminal_result.json"
    artifact_manifest_path: str = "/workspace/output/artifact_manifest.json"
    artifact_dir: str = "/workspace/output/artifacts"

    def as_environment(self) -> dict[str, str]:
        return {
            "ATLAS_RUNSPEC_PATH": self.run_spec_path,
            "ATLAS_EVENTS_PATH": self.events_path,
            "ATLAS_TERMINAL_RESULT_PATH": self.terminal_result_path,
            "ATLAS_ARTIFACT_MANIFEST_PATH": self.artifact_manifest_path,
            "ATLAS_ARTIFACT_DIR": self.artifact_dir,
        }

    def as_entrypoint_args(self) -> list[str]:
        return [
            "--run-spec",
            self.run_spec_path,
            "--events",
            self.events_path,
            "--terminal-result",
            self.terminal_result_path,
            "--artifact-manifest",
            self.artifact_manifest_path,
            "--artifact-dir",
            self.artifact_dir,
        ]


class TracingExportConfig(BaseModel):
    protocol: str = "otlp_http"
    endpoint: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)


class TracingConfig(BaseModel):
    backend: str | None = None
    project_name: str | None = None
    export: TracingExportConfig | None = None


class RunSpec(BaseModel):
    schema_version: Literal["run-spec.v1"] = "run-spec.v1"
    run_id: UUID
    experiment_id: UUID | None = None
    dataset_version_id: UUID | None = None
    dataset_sample_id: str | None = None
    attempt: int = 1
    attempt_id: UUID | None = None
    project: str
    dataset: str | None = None
    agent_id: str = ""
    model: str
    entrypoint: str | None = None
    agent_type: str
    input_summary: str
    prompt: str
    tags: list[str] = Field(default_factory=list)
    project_metadata: dict[str, Any] = Field(default_factory=dict)
    model_settings: dict[str, Any] | None = None
    prompt_config: dict[str, Any] | None = None
    toolset_config: dict[str, Any] = Field(default_factory=dict)
    evaluator_config: dict[str, Any] = Field(default_factory=dict)
    executor_config: dict[str, Any] = Field(default_factory=dict)
    approval_policy: dict[str, Any] | None = None
    framework: str | None = None
    framework_type: str | None = None
    framework_version: str | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None
    trace_backend: str | None = None
    tracing: TracingConfig | None = None
    published_agent_snapshot: dict[str, Any]
    bootstrap: RunnerBootstrapPaths = Field(default_factory=RunnerBootstrapPaths)


class EvalResult(BaseModel):
    schema_version: Literal["eval-result.v1"] = "eval-result.v1"
    run_id: UUID
    experiment_id: UUID | None = None
    dataset_version_id: UUID | None = None
    dataset_sample_id: str | None = None
    attempt: int = 1
    attempt_id: UUID | None = None
    status: str = "completed"
    judgement: str | None = None
    score: float | None = None
    evaluator_name: str | None = None
    evaluator_version: str | None = None
    trace_uri: str | None = None
    failure_reason: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    ts: datetime = Field(default_factory=utc_now)
    metrics: dict[str, Any] = Field(default_factory=dict)
    labels: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExportShard(BaseModel):
    uri: str
    row_count: int = 0
    size_bytes: int | None = None
    sha256: str | None = None
    partition: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExportManifest(BaseModel):
    schema_version: Literal["export-manifest.v1"] = "export-manifest.v1"
    export_id: UUID
    created_at: datetime = Field(default_factory=utc_now)
    format: str
    row_schema_version: str | None = None
    dataset_version_id: UUID | None = None
    source_experiment_id: UUID | None = None
    baseline_experiment_id: UUID | None = None
    candidate_experiment_id: UUID | None = None
    row_count: int = 0
    shards: list[ExportShard] = Field(default_factory=list)
    filters_summary: dict[str, Any] = Field(default_factory=dict)
    lineage: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunnerRunSpec(RunSpec):
    # Compatibility alias while the repo migrates to the neutral RunSpec name.
    schema_version: Literal["runner-run-spec.v1", "run-spec.v1"] = "runner-run-spec.v1"


__all__ = [
    "ArtifactEntry",
    "ArtifactManifest",
    "EvalResult",
    "EventEnvelope",
    "ExportManifest",
    "ExportShard",
    "ProducerInfo",
    "RunSpec",
    "RunnerBootstrapPaths",
    "RunnerRunSpec",
    "TerminalMetrics",
    "TerminalResult",
    "TracingConfig",
    "TracingExportConfig",
]
