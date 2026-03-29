from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.modules.shared.domain.enums import AdapterKind, RunStatus, StepType
from app.modules.shared.domain.models import (
    ApprovalPolicySnapshot,
    EvaluatorConfig,
    ExecutorConfig,
    ModelConfig,
    ObservabilityMetadata,
    PromptConfig,
    ProvenanceMetadata,
    RunLineage,
    ToolsetConfig,
    TracePointer,
)


class RunSpec(BaseModel):
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
    model_settings: ModelConfig | None = Field(
        default=None,
        alias="model_config",
        serialization_alias="model_config",
    )
    prompt_config: PromptConfig | None = None
    toolset_config: ToolsetConfig = Field(default_factory=ToolsetConfig)
    evaluator_config: EvaluatorConfig = Field(default_factory=EvaluatorConfig)
    executor_config: ExecutorConfig = Field(
        default_factory=lambda: ExecutorConfig(backend="local-runner")
    )
    approval_policy: ApprovalPolicySnapshot | None = None
    provenance: ProvenanceMetadata | None = None


class RunCreateInput(BaseModel):
    experiment_id: UUID | None = None
    dataset_version_id: UUID | None = None
    project: str
    dataset: str | None = None
    agent_id: str
    input_summary: str
    prompt: str
    tags: list[str] = Field(default_factory=list)
    project_metadata: dict[str, Any] = Field(default_factory=dict)
    dataset_sample_id: str | None = None
    executor_backend: str = "local-runner"
    executor_config: ExecutorConfig | None = None
    model_settings: ModelConfig | None = Field(
        default=None,
        alias="model_config",
        serialization_alias="model_config",
    )
    prompt_config: PromptConfig | None = None
    toolset_config: ToolsetConfig = Field(default_factory=ToolsetConfig)
    evaluator_config: EvaluatorConfig = Field(default_factory=EvaluatorConfig)
    approval_policy: ApprovalPolicySnapshot | None = None


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
    resolved_model: str | None = None


class ResolvedRunArtifact(BaseModel):
    framework: str | None = None
    entrypoint: str | None = None
    source_fingerprint: str | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None
    published_agent_snapshot: dict[str, Any]


class RunnerExecutionHandoff(BaseModel):
    run_id: UUID
    runner_backend: str
    experiment_id: UUID | None = None
    dataset_version_id: UUID | None = None
    project: str
    dataset: str | None = None
    agent_id: str
    model: str
    entrypoint: str | None = None
    agent_type: AdapterKind
    input_summary: str
    prompt: str
    tags: list[str] = Field(default_factory=list)
    project_metadata: dict[str, Any] = Field(default_factory=dict)
    dataset_sample_id: str | None = None
    framework: str | None = None
    framework_type: str | None = None
    framework_version: str | None = None
    source_fingerprint: str | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None
    trace_backend: str | None = None
    published_agent_snapshot: dict[str, Any]
    toolset_config: ToolsetConfig = Field(default_factory=ToolsetConfig)
    evaluator_config: EvaluatorConfig = Field(default_factory=EvaluatorConfig)
    executor_config: ExecutorConfig = Field(
        default_factory=lambda: ExecutorConfig(backend="local-runner")
    )
    approval_policy: ApprovalPolicySnapshot | None = None

    @classmethod
    def from_spec(
        cls,
        *,
        run_id: UUID,
        payload: RunSpec,
        artifact: ResolvedRunArtifact,
        runner_backend: str,
    ) -> RunnerExecutionHandoff:
        provenance = payload.provenance
        return cls(
            run_id=run_id,
            runner_backend=runner_backend,
            experiment_id=payload.experiment_id,
            dataset_version_id=payload.dataset_version_id,
            project=payload.project,
            dataset=payload.dataset,
            agent_id=payload.agent_id,
            model=payload.model,
            entrypoint=artifact.entrypoint or payload.entrypoint,
            agent_type=payload.agent_type,
            input_summary=payload.input_summary,
            prompt=payload.prompt,
            tags=list(payload.tags),
            project_metadata=dict(payload.project_metadata),
            dataset_sample_id=payload.dataset_sample_id,
            framework=artifact.framework,
            framework_type=artifact.framework,
            framework_version=(
                provenance.framework_version
                if provenance and provenance.framework_version is not None
                else "1.0.0"
            ),
            source_fingerprint=artifact.source_fingerprint,
            artifact_ref=artifact.artifact_ref,
            image_ref=artifact.image_ref,
            trace_backend=provenance.trace_backend if provenance else None,
            published_agent_snapshot=artifact.published_agent_snapshot,
            toolset_config=payload.toolset_config.model_copy(deep=True),
            evaluator_config=payload.evaluator_config.model_copy(deep=True),
            executor_config=payload.executor_config.model_copy(deep=True),
            approval_policy=(
                payload.approval_policy.model_copy(deep=True)
                if payload.approval_policy is not None
                else None
            ),
        )

    def to_run_spec(self) -> RunSpec:
        return RunSpec(
            run_id=self.run_id,
            experiment_id=self.experiment_id,
            dataset_version_id=self.dataset_version_id,
            project=self.project,
            dataset=self.dataset,
            agent_id=self.agent_id,
            model=self.model,
            entrypoint=self.entrypoint,
            agent_type=self.agent_type,
            input_summary=self.input_summary,
            prompt=self.prompt,
            tags=list(self.tags),
            project_metadata=dict(self.project_metadata),
            dataset_sample_id=self.dataset_sample_id,
            toolset_config=self.toolset_config.model_copy(deep=True),
            evaluator_config=self.evaluator_config.model_copy(deep=True),
            executor_config=self.executor_config.model_copy(deep=True),
            approval_policy=(
                self.approval_policy.model_copy(deep=True)
                if self.approval_policy is not None
                else None
            ),
            provenance=ProvenanceMetadata(
                framework=self.framework,
                framework_type=self.framework_type,
                framework_version=self.framework_version,
                published_agent_snapshot=self.published_agent_snapshot,
                artifact_ref=self.artifact_ref,
                image_ref=self.image_ref,
                runner_backend=self.runner_backend,
                executor_backend=self.executor_config.backend,
                trace_backend=self.trace_backend,
                experiment_id=self.experiment_id,
                dataset_version_id=self.dataset_version_id,
                dataset_sample_id=self.dataset_sample_id,
                approval_policy=(
                    self.approval_policy.model_copy(deep=True)
                    if self.approval_policy is not None
                    else None
                ),
                toolset=self.toolset_config.model_copy(deep=True),
                evaluator=self.evaluator_config.model_copy(deep=True),
                executor=self.executor_config.model_copy(deep=True),
            ),
        )


def utc_now() -> datetime:
    return datetime.now(UTC)


class RunRecord(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    experiment_id: UUID | None = None
    dataset_version_id: UUID | None = None
    input_summary: str
    status: RunStatus = RunStatus.QUEUED
    latency_ms: int = 0
    token_cost: int = 0
    tool_calls: int = 0
    project: str
    dataset: str | None = None
    dataset_sample_id: str | None = None
    agent_id: str = ""
    model: str
    entrypoint: str | None = None
    agent_type: AdapterKind
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    project_metadata: dict[str, Any] = Field(default_factory=dict)
    artifact_ref: str | None = None
    image_ref: str | None = None
    executor_backend: str | None = None
    executor_submission_id: str | None = None
    attempt: int = 1
    runner_backend: str | None = None
    execution_backend: str | None = None
    container_image: str | None = None
    provenance: ProvenanceMetadata | None = None
    observability: ObservabilityMetadata | None = None
    trace_pointer: TracePointer | None = None
    lineage: RunLineage | None = None
    resolved_model: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    termination_reason: str | None = None
    terminal_reason: str | None = None


class TrajectoryStep(BaseModel):
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
