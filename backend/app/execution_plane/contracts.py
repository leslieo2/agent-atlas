from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.runs.domain.models import RunnerExecutionHandoff, RunSpec


def utc_now() -> datetime:
    return datetime.now(UTC)


class ProducerInfo(BaseModel):
    kind: str = "runner"
    runtime: str | None = None
    framework: str | None = None
    language: str | None = None
    version: str | None = None


class EventEnvelope(BaseModel):
    schema_version: str = "runner-event.v1"
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
    schema_version: str = "runner-artifact-manifest.v1"
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
    schema_version: str = "runner-terminal-result.v1"
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


class RunnerRunSpec(BaseModel):
    schema_version: str = "runner-run-spec.v1"
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
    published_agent_snapshot: dict[str, Any]
    bootstrap: RunnerBootstrapPaths = Field(default_factory=RunnerBootstrapPaths)

    @classmethod
    def from_run_spec(
        cls,
        payload: RunSpec,
        *,
        attempt: int = 1,
        attempt_id: UUID | None = None,
        bootstrap: RunnerBootstrapPaths | None = None,
    ) -> RunnerRunSpec:
        provenance = payload.provenance
        published_agent_snapshot = (
            provenance.published_agent_snapshot
            if provenance is not None and provenance.published_agent_snapshot is not None
            else {}
        )
        return cls(
            run_id=payload.run_id,
            experiment_id=payload.experiment_id,
            dataset_version_id=payload.dataset_version_id,
            dataset_sample_id=payload.dataset_sample_id,
            attempt=attempt,
            attempt_id=attempt_id,
            project=payload.project,
            dataset=payload.dataset,
            agent_id=payload.agent_id,
            model=payload.model,
            entrypoint=payload.entrypoint,
            agent_type=payload.agent_type.value,
            input_summary=payload.input_summary,
            prompt=payload.prompt,
            tags=list(payload.tags),
            project_metadata=dict(payload.project_metadata),
            model_settings=(
                payload.model_settings.model_dump(mode="json")
                if payload.model_settings is not None
                else None
            ),
            prompt_config=(
                payload.prompt_config.model_dump(mode="json")
                if payload.prompt_config is not None
                else None
            ),
            toolset_config=payload.toolset_config.model_dump(mode="json"),
            evaluator_config=payload.evaluator_config.model_dump(mode="json"),
            executor_config=payload.executor_config.model_dump(mode="json"),
            approval_policy=(
                payload.approval_policy.model_dump(mode="json")
                if payload.approval_policy is not None
                else None
            ),
            framework=provenance.framework if provenance is not None else None,
            framework_type=provenance.framework_type if provenance is not None else None,
            framework_version=provenance.framework_version if provenance is not None else None,
            artifact_ref=provenance.artifact_ref if provenance is not None else None,
            image_ref=provenance.image_ref if provenance is not None else None,
            trace_backend=provenance.trace_backend if provenance is not None else None,
            published_agent_snapshot=published_agent_snapshot,
            bootstrap=bootstrap or RunnerBootstrapPaths(),
        )

    @classmethod
    def from_handoff(cls, handoff: RunnerExecutionHandoff) -> RunnerRunSpec:
        return cls(
            run_id=handoff.run_id,
            experiment_id=handoff.experiment_id,
            dataset_version_id=handoff.dataset_version_id,
            dataset_sample_id=handoff.dataset_sample_id,
            attempt=handoff.attempt,
            attempt_id=handoff.attempt_id,
            project=handoff.project,
            dataset=handoff.dataset,
            agent_id=handoff.agent_id,
            model=handoff.model,
            entrypoint=handoff.entrypoint,
            agent_type=handoff.agent_type.value,
            input_summary=handoff.input_summary,
            prompt=handoff.prompt,
            tags=list(handoff.tags),
            project_metadata=dict(handoff.project_metadata),
            model_settings=(
                handoff.model_settings.model_dump(mode="json")
                if handoff.model_settings is not None
                else None
            ),
            prompt_config=(
                handoff.prompt_config.model_dump(mode="json")
                if handoff.prompt_config is not None
                else None
            ),
            toolset_config=handoff.toolset_config.model_dump(mode="json"),
            evaluator_config=handoff.evaluator_config.model_dump(mode="json"),
            executor_config=handoff.executor_config.model_dump(mode="json"),
            approval_policy=(
                handoff.approval_policy.model_dump(mode="json")
                if handoff.approval_policy is not None
                else None
            ),
            framework=handoff.framework,
            framework_type=handoff.framework_type,
            framework_version=handoff.framework_version,
            artifact_ref=handoff.artifact_ref,
            image_ref=handoff.image_ref,
            trace_backend=handoff.trace_backend,
            published_agent_snapshot=handoff.published_agent_snapshot,
        )
