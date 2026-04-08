from __future__ import annotations

from collections.abc import Mapping

from agent_atlas_contracts.runtime import AgentLoadFailedError

from app.core.errors import (
    UnsupportedOperationError,
)
from app.execution.application.ports import ExecutionControlPort
from app.execution.metadata import requested_runner_backend, runner_image, uses_k8s_runner_backend
from app.modules.agents.domain.models import GovernedPublishedAgent
from app.modules.runs.application.ports import RunRepository
from app.modules.runs.domain.models import RunCreateInput, RunExecutionSpec, RunRecord
from app.modules.runs.domain.policies import RunAggregate
from app.modules.shared.domain.constants import EXTERNAL_RUNNER_EXECUTION_BACKEND
from app.modules.shared.domain.execution import ExecutionBinding, ExecutionProfile
from app.modules.shared.domain.provenance import ProvenanceMetadata


def _deep_merge_values(base: object, override: object) -> object:
    if isinstance(base, Mapping) and isinstance(override, Mapping):
        merged = dict(base)
        for key, value in override.items():
            if key in merged:
                merged[key] = _deep_merge_values(merged[key], value)
            else:
                merged[key] = value
        return merged
    return override


def _resolve_submission_agent(agent: GovernedPublishedAgent) -> GovernedPublishedAgent:
    try:
        agent.source_fingerprint_or_raise()
        agent.execution_reference_or_raise()
    except ValueError as exc:
        raise AgentLoadFailedError(str(exc), agent_id=agent.agent_id) from exc

    return agent


def _resolved_submission_provenance(
    effective_agent: GovernedPublishedAgent,
    *,
    trace_backend: str,
) -> ProvenanceMetadata:
    try:
        source_fingerprint = effective_agent.source_fingerprint_or_raise()
        execution_reference = effective_agent.execution_reference_or_raise()
    except ValueError as exc:
        raise AgentLoadFailedError(
            str(exc),
            agent_id=effective_agent.agent_id,
        ) from exc
    snapshot = effective_agent.model_copy(
        update={
            "source_fingerprint": source_fingerprint,
            "execution_reference": execution_reference,
            "default_runtime_profile": effective_agent.default_runtime_profile.model_copy(
                deep=True
            ),
        },
        deep=True,
    ).to_snapshot()
    provenance = ProvenanceMetadata()
    provenance.agent_family = effective_agent.agent_family
    provenance.framework = effective_agent.framework
    provenance.framework_version = effective_agent.framework_version
    provenance.published_agent_snapshot = snapshot
    provenance.artifact_ref = execution_reference.artifact_ref
    provenance.image_ref = execution_reference.image_ref
    provenance.trace_backend = trace_backend
    return provenance


def _resolve_executor_config(
    payload: RunCreateInput,
    *,
    default_execution_binding: ExecutionBinding | None,
    default_runtime_profile: ExecutionProfile,
    default_trace_backend: str,
) -> tuple[ExecutionProfile, ExecutionBinding | None, str]:
    executor_config = default_runtime_profile.model_copy(deep=True)
    execution_binding = (
        default_execution_binding.model_copy(deep=True)
        if default_execution_binding is not None
        else (
            default_runtime_profile.execution_binding.model_copy(deep=True)
            if default_runtime_profile.execution_binding is not None
            else None
        )
    )
    if "executor_config" in payload.model_fields_set:
        merged_config = _deep_merge_values(
            executor_config.model_dump(mode="python"),
            payload.executor_config.model_dump(mode="python", exclude_unset=True),
        )
        executor_config = ExecutionProfile.model_validate(merged_config)
        if payload.executor_config.execution_binding is not None:
            base_binding = (
                execution_binding.model_dump(mode="python", exclude_none=True)
                if execution_binding is not None
                else {}
            )
            override_binding = payload.executor_config.execution_binding.model_dump(
                mode="python",
                exclude_none=True,
            )
            execution_binding = ExecutionBinding.model_validate(
                _deep_merge_values(base_binding, override_binding)
            )
    if payload.execution_binding is not None:
        base_binding = (
            execution_binding.model_dump(mode="python", exclude_none=True)
            if execution_binding is not None
            else {}
        )
        override_binding = payload.execution_binding.model_dump(mode="python", exclude_none=True)
        execution_binding = ExecutionBinding.model_validate(
            _deep_merge_values(base_binding, override_binding)
        )
    explicit_tracing_backend = (
        payload.executor_config.tracing_backend
        if (
            "executor_config" in payload.model_fields_set
            and "tracing_backend" in payload.executor_config.model_fields_set
        )
        else None
    )
    profile_tracing_backend = (
        executor_config.tracing_backend
        if "tracing_backend" in default_runtime_profile.model_fields_set
        else None
    )
    trace_backend = explicit_tracing_backend or profile_tracing_backend or default_trace_backend
    resolved_executor_config = executor_config.model_copy(
        update={"tracing_backend": trace_backend},
        deep=True,
    )
    return resolved_executor_config, execution_binding, trace_backend


def _validate_execution_backend(
    *,
    executor_config: ExecutionProfile,
    execution_binding: ExecutionBinding | None,
    agent_id: str,
) -> None:
    normalized_backend = executor_config.backend.strip().lower()
    execution_view: ExecutionProfile | Mapping[str, object]
    if execution_binding is None:
        execution_view = executor_config
    else:
        execution_view = {
            "backend": executor_config.backend,
            "tracing_backend": executor_config.tracing_backend,
            "execution_binding": execution_binding,
        }
    if (
        normalized_backend == EXTERNAL_RUNNER_EXECUTION_BACKEND
        and not uses_k8s_runner_backend(execution_view)
        and requested_runner_backend(execution_view) is None
    ):
        raise UnsupportedOperationError(
            "external-runner execution requires explicit carrier metadata",
            agent_id=agent_id,
            executor_backend=executor_config.backend,
        )
    requires_runner_image = normalized_backend == "k8s-job" or (
        normalized_backend == EXTERNAL_RUNNER_EXECUTION_BACKEND
        and uses_k8s_runner_backend(execution_view)
    )
    if not requires_runner_image:
        return

    configured_runner_image = runner_image(execution_view) or ""
    if configured_runner_image:
        return

    raise UnsupportedOperationError(
        "k8s-carried execution requires execution binding runner_image",
        agent_id=agent_id,
        executor_backend=executor_config.backend,
    )


class RunSubmissionService:
    def __init__(
        self,
        run_repository: RunRepository,
        execution_control: ExecutionControlPort,
        default_trace_backend: str = "state",
    ) -> None:
        self.run_repository = run_repository
        self.execution_control = execution_control
        self.default_trace_backend = default_trace_backend

    def submit(self, payload: RunCreateInput, agent: GovernedPublishedAgent) -> RunRecord:
        effective_agent = _resolve_submission_agent(agent)
        executor_config, execution_binding, trace_backend = _resolve_executor_config(
            payload,
            default_execution_binding=effective_agent.execution_binding,
            default_runtime_profile=effective_agent.default_runtime_profile,
            default_trace_backend=self.default_trace_backend,
        )
        provenance = _resolved_submission_provenance(
            effective_agent,
            trace_backend=trace_backend,
        )
        _validate_execution_backend(
            executor_config=executor_config,
            execution_binding=execution_binding,
            agent_id=payload.agent_id,
        )
        provenance.executor_backend = executor_config.backend
        provenance.experiment_id = payload.experiment_id
        provenance.dataset_version_id = payload.dataset_version_id
        provenance.dataset_sample_id = payload.dataset_sample_id
        provenance.execution_target = (
            payload.execution_target.model_copy(deep=True)
            if payload.execution_target is not None
            else None
        )
        provenance.approval_policy = (
            payload.approval_policy.model_copy(deep=True) if payload.approval_policy else None
        )
        provenance.toolset = payload.toolset_config.model_copy(deep=True)
        provenance.evaluator = payload.evaluator_config.model_copy(deep=True)
        provenance.executor = executor_config.model_copy(deep=True)
        spec = RunExecutionSpec(
            experiment_id=payload.experiment_id,
            dataset_version_id=payload.dataset_version_id,
            project=payload.project,
            dataset=payload.dataset,
            dataset_sample_id=payload.dataset_sample_id,
            agent_id=payload.agent_id,
            model=(
                payload.model_settings.model
                if payload.model_settings is not None
                else effective_agent.default_model
            ),
            entrypoint=effective_agent.entrypoint,
            agent_type=effective_agent.adapter_kind(),
            input_summary=payload.input_summary,
            prompt=payload.prompt,
            tags=list(payload.tags),
            project_metadata=dict(payload.project_metadata),
            execution_target=(
                payload.execution_target.model_copy(deep=True)
                if payload.execution_target is not None
                else (
                    provenance.execution_target.model_copy(deep=True)
                    if provenance.execution_target is not None
                    else None
                )
            ),
            executor_config=executor_config,
            execution_binding=execution_binding,
            model_settings=payload.model_settings,
            prompt_config=payload.prompt_config,
            toolset_config=payload.toolset_config,
            evaluator_config=payload.evaluator_config,
            approval_policy=payload.approval_policy,
            provenance=provenance,
        )
        run = RunAggregate.create(spec)
        self.run_repository.save(run)
        handle = self.execution_control.submit_run(spec)
        updated = run.model_copy(
            update={
                "attempt_id": handle.attempt_id,
                "executor_backend": handle.backend,
                "executor_submission_id": handle.executor_ref,
            }
        )
        self.run_repository.save(updated)
        return updated
