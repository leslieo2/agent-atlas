from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from agent_atlas_contracts.execution import (
    ExecutionArtifact,
    ExecutionHandoff,
    RunnerBootstrapPaths,
    RunnerRunSpec,
    TracingConfig,
    TracingExportConfig,
)
from pydantic import BaseModel, Field

from app.core.config import settings
from app.modules.shared.domain.enums import AdapterKind, RunStatus
from app.modules.shared.domain.models import (
    ApprovalPolicySnapshot,
    EvaluatorConfig,
    ExecutorConfig,
    ModelConfig,
    PromptConfig,
    ProvenanceMetadata,
    ToolsetConfig,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class ExecutionCapability(BaseModel):
    backend: str
    production_ready: bool
    supports_cancel: bool
    supports_retry: bool
    supports_status: bool
    supports_heartbeat: bool


class RunHandle(BaseModel):
    run_id: UUID
    attempt_id: UUID = Field(default_factory=uuid4)
    backend: str
    executor_ref: str
    submitted_at: datetime = Field(default_factory=utc_now)


class CancelRequest(BaseModel):
    run_id: UUID
    attempt_id: UUID | None = None
    reason: str = "cancelled by user"


class Heartbeat(BaseModel):
    run_id: UUID
    attempt_id: UUID
    backend: str
    sequence: int
    status: RunStatus
    occurred_at: datetime = Field(default_factory=utc_now)
    lease_expires_at: datetime | None = None
    last_progress_at: datetime | None = None
    phase_hint: str | None = None


class RunTerminalSummary(BaseModel):
    run_id: UUID
    attempt_id: UUID
    status: RunStatus
    backend: str
    reason_code: str | None = None
    reason_message: str | None = None
    exit_code: int | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None
    trace_url: str | None = None
    started_at: datetime | None = None
    completed_at: datetime = Field(default_factory=utc_now)


class RunStatusSnapshot(BaseModel):
    run_id: UUID
    attempt_id: UUID | None = None
    backend: str | None = None
    executor_ref: str | None = None
    status: RunStatus
    reason_code: str | None = None
    reason_message: str | None = None
    heartbeat: Heartbeat | None = None
    terminal_summary: RunTerminalSummary | None = None


class ExecutionRunSpec(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    experiment_id: UUID | None = None
    dataset_version_id: UUID | None = None
    project: str
    dataset: str | None = None
    agent_id: str = ""
    model: str
    entrypoint: str | None = None
    agent_type: AdapterKind
    input_summary: str
    prompt: str
    tags: list[str] = Field(default_factory=list)
    project_metadata: dict[str, Any] = Field(default_factory=dict)
    dataset_sample_id: str | None = None
    model_settings: ModelConfig | None = None
    prompt_config: PromptConfig | None = None
    toolset_config: ToolsetConfig = Field(default_factory=ToolsetConfig)
    evaluator_config: EvaluatorConfig = Field(default_factory=EvaluatorConfig)
    executor_config: ExecutorConfig = Field(
        default_factory=lambda: ExecutorConfig(backend="local-runner")
    )
    approval_policy: ApprovalPolicySnapshot | None = None
    provenance: ProvenanceMetadata | None = None


def _runner_tracing_config(trace_backend: str | None) -> TracingConfig | None:
    if not settings.tracing_otlp_endpoint:
        return None
    return TracingConfig(
        backend=trace_backend,
        project_name=settings.tracing_project_name,
        export=TracingExportConfig(
            endpoint=settings.tracing_otlp_endpoint,
            headers=dict(settings.tracing_headers),
        ),
    )


def runner_run_spec_from_run_spec(
    payload: ExecutionRunSpec,
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
    return RunnerRunSpec(
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
        prompt=payload.prompt,
        tags=list(payload.tags),
        project_metadata=dict(payload.project_metadata),
        executor_config=payload.executor_config.model_dump(mode="json"),
        framework=provenance.framework if provenance is not None else None,
        artifact_ref=provenance.artifact_ref if provenance is not None else None,
        image_ref=provenance.image_ref if provenance is not None else None,
        trace_backend=provenance.trace_backend if provenance is not None else None,
        tracing=_runner_tracing_config(
            provenance.trace_backend if provenance is not None else None
        ),
        published_agent_snapshot=published_agent_snapshot,
        bootstrap=bootstrap or RunnerBootstrapPaths(),
    )


def execution_handoff_from_run_spec(
    *,
    run_id: UUID,
    payload: ExecutionRunSpec,
    artifact: ExecutionArtifact,
    runner_backend: str,
    attempt: int = 1,
    attempt_id: UUID | None = None,
) -> ExecutionHandoff:
    provenance = payload.provenance
    return ExecutionHandoff(
        run_id=run_id,
        runner_backend=runner_backend,
        experiment_id=payload.experiment_id,
        dataset_version_id=payload.dataset_version_id,
        dataset_sample_id=payload.dataset_sample_id,
        attempt=attempt,
        attempt_id=attempt_id,
        project=payload.project,
        dataset=payload.dataset,
        agent_id=payload.agent_id,
        model=payload.model,
        entrypoint=artifact.entrypoint or payload.entrypoint,
        agent_type=payload.agent_type.value,
        prompt=payload.prompt,
        tags=list(payload.tags),
        project_metadata=dict(payload.project_metadata),
        executor_config=payload.executor_config.model_dump(mode="json"),
        framework=artifact.framework,
        artifact_ref=artifact.artifact_ref,
        image_ref=artifact.image_ref,
        trace_backend=provenance.trace_backend if provenance else None,
        published_agent_snapshot=dict(artifact.published_agent_snapshot),
    )


def runner_run_spec_from_handoff(handoff: ExecutionHandoff) -> RunnerRunSpec:
    return RunnerRunSpec(
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
        agent_type=handoff.agent_type,
        prompt=handoff.prompt,
        tags=list(handoff.tags),
        project_metadata=dict(handoff.project_metadata),
        executor_config=dict(handoff.executor_config),
        framework=handoff.framework,
        artifact_ref=handoff.artifact_ref,
        image_ref=handoff.image_ref,
        trace_backend=handoff.trace_backend,
        tracing=_runner_tracing_config(handoff.trace_backend),
        published_agent_snapshot=handoff.published_agent_snapshot,
    )
