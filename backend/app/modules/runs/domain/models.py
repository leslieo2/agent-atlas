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
    attempt: int = 1
    attempt_id: UUID | None = None
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
    model_settings: ModelConfig | None = None
    prompt_config: PromptConfig | None = None
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
        attempt: int = 1,
        attempt_id: UUID | None = None,
    ) -> RunnerExecutionHandoff:
        provenance = payload.provenance
        return cls(
            run_id=run_id,
            runner_backend=runner_backend,
            experiment_id=payload.experiment_id,
            dataset_version_id=payload.dataset_version_id,
            attempt=attempt,
            attempt_id=attempt_id,
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
            model_settings=(
                payload.model_settings.model_copy(deep=True)
                if payload.model_settings is not None
                else None
            ),
            prompt_config=(
                payload.prompt_config.model_copy(deep=True)
                if payload.prompt_config is not None
                else None
            ),
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
            model_config=(
                self.model_settings.model_copy(deep=True)
                if self.model_settings is not None
                else None
            ),
            prompt_config=(
                self.prompt_config.model_copy(deep=True) if self.prompt_config is not None else None
            ),
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
    attempt_id: UUID = Field(default_factory=uuid4)
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
    started_at: datetime | None = None
    completed_at: datetime | None = None
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
    last_heartbeat_at: datetime | None = None
    last_progress_at: datetime | None = None
    lease_expires_at: datetime | None = None
    heartbeat_sequence: int = 0

    def to_run_spec(self) -> RunSpec:
        prompt = str(self.project_metadata.get("prompt", ""))
        project_metadata = dict(self.project_metadata)
        project_metadata.pop("prompt", None)
        provenance = self.provenance.model_copy(deep=True) if self.provenance is not None else None
        prompt_version = project_metadata.get("prompt_version")
        system_prompt = project_metadata.get("system_prompt")
        model_config = None
        prompt_config = None
        toolset_config = ToolsetConfig()
        evaluator_config = EvaluatorConfig()
        executor_config = ExecutorConfig(backend=self.executor_backend or "local-runner")
        approval_policy = None
        if provenance is not None:
            model_config = ModelConfig(model=self.resolved_model or self.model)
            prompt_config = PromptConfig(
                prompt_version=prompt_version if isinstance(prompt_version, str) else None,
                system_prompt=system_prompt if isinstance(system_prompt, str) else None,
            )
            toolset_config = (
                provenance.toolset.model_copy(deep=True)
                if provenance.toolset is not None
                else ToolsetConfig()
            )
            evaluator_config = (
                provenance.evaluator.model_copy(deep=True)
                if provenance.evaluator is not None
                else EvaluatorConfig()
            )
            executor_config = (
                provenance.executor.model_copy(deep=True)
                if provenance.executor is not None
                else ExecutorConfig(backend=self.executor_backend or "local-runner")
            )
            approval_policy = (
                provenance.approval_policy.model_copy(deep=True)
                if provenance.approval_policy is not None
                else None
            )
            provenance = provenance.model_copy(
                update={
                    "artifact_ref": self.artifact_ref,
                    "image_ref": self.image_ref,
                    "executor_backend": self.executor_backend,
                }
            )

        return RunSpec(
            run_id=self.run_id,
            experiment_id=self.experiment_id,
            dataset_version_id=self.dataset_version_id,
            project=self.project,
            dataset=self.dataset,
            agent_id=self.agent_id,
            model=self.resolved_model or self.model,
            entrypoint=self.entrypoint,
            agent_type=self.agent_type,
            input_summary=self.input_summary,
            prompt=prompt,
            tags=list(self.tags),
            project_metadata=project_metadata,
            dataset_sample_id=self.dataset_sample_id,
            model_config=model_config,
            prompt_config=prompt_config,
            toolset_config=toolset_config,
            evaluator_config=evaluator_config,
            executor_config=executor_config,
            approval_policy=approval_policy,
            provenance=provenance,
        )


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
