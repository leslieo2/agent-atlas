from __future__ import annotations

from app.core.errors import AgentFrameworkMismatchError, AgentLoadFailedError
from app.execution.application.ports import ExecutionControlPort
from app.execution.contracts import ExecutionRunSpec
from app.modules.agents.domain.models import PublishedAgent
from app.modules.runs.application.ports import RunRepository
from app.modules.runs.domain.models import RunCreateInput, RunRecord
from app.modules.runs.domain.policies import RunAggregate
from app.modules.shared.domain.models import ExecutorConfig, ProvenanceMetadata


def _resolve_submission_agent(agent: PublishedAgent) -> PublishedAgent:
    provenance = agent.provenance
    snapshot = provenance.published_agent_snapshot if provenance else None
    if snapshot is None:
        return agent

    try:
        published_snapshot = PublishedAgent.model_validate(snapshot)
    except Exception as exc:
        raise AgentLoadFailedError(
            "published agent is missing a valid snapshot",
            agent_id=agent.agent_id,
        ) from exc

    if published_snapshot.agent_id != agent.agent_id:
        raise AgentFrameworkMismatchError(
            "published agent snapshot does not match the stored agent identifier",
            agent_id=agent.agent_id,
            snapshot_agent_id=published_snapshot.agent_id,
        )

    if published_snapshot.framework != agent.framework:
        raise AgentFrameworkMismatchError(
            "published agent snapshot framework does not match stored agent metadata",
            agent_id=agent.agent_id,
            expected_framework=published_snapshot.framework,
            actual_framework=agent.framework,
        )

    if provenance and provenance.framework and provenance.framework != published_snapshot.framework:
        raise AgentFrameworkMismatchError(
            "published agent provenance framework does not match the published snapshot",
            agent_id=agent.agent_id,
            expected_framework=published_snapshot.framework,
            actual_framework=provenance.framework,
        )

    return published_snapshot


def _resolved_submission_provenance(
    agent: PublishedAgent,
    effective_agent: PublishedAgent,
    *,
    trace_backend: str,
) -> ProvenanceMetadata:
    runtime_artifact = agent.effective_runtime_artifact()
    provenance = (
        agent.provenance.model_copy(deep=True) if agent.provenance else ProvenanceMetadata()
    )
    snapshot = effective_agent.model_copy(
        update={"runtime_artifact": runtime_artifact},
        deep=True,
    ).to_snapshot()
    provenance.framework = runtime_artifact.framework or effective_agent.framework
    provenance.published_agent_snapshot = snapshot
    provenance.artifact_ref = runtime_artifact.artifact_ref
    provenance.image_ref = runtime_artifact.image_ref
    provenance.trace_backend = trace_backend
    return provenance


def _resolve_executor_config(
    payload: RunCreateInput,
    *,
    default_trace_backend: str,
) -> tuple[ExecutorConfig, str]:
    if payload.executor_config is None:
        executor_config = ExecutorConfig(
            backend=payload.executor_backend,
            tracing_backend=default_trace_backend,
        )
        return executor_config, default_trace_backend

    explicit_tracing_backend = (
        payload.executor_config.tracing_backend
        if "tracing_backend" in payload.executor_config.model_fields_set
        else None
    )
    trace_backend = explicit_tracing_backend or default_trace_backend
    executor_config = payload.executor_config.model_copy(
        update={"tracing_backend": trace_backend},
        deep=True,
    )
    return executor_config, trace_backend


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

    def submit(self, payload: RunCreateInput, agent: PublishedAgent) -> RunRecord:
        effective_agent = _resolve_submission_agent(agent)
        executor_config, trace_backend = _resolve_executor_config(
            payload,
            default_trace_backend=self.default_trace_backend,
        )
        provenance = _resolved_submission_provenance(
            agent,
            effective_agent,
            trace_backend=trace_backend,
        )
        provenance.framework_type = provenance.framework
        provenance.executor_backend = executor_config.backend
        provenance.experiment_id = payload.experiment_id
        provenance.dataset_version_id = payload.dataset_version_id
        provenance.dataset_sample_id = payload.dataset_sample_id
        provenance.approval_policy = (
            payload.approval_policy.model_copy(deep=True) if payload.approval_policy else None
        )
        provenance.toolset = payload.toolset_config.model_copy(deep=True)
        provenance.evaluator = payload.evaluator_config.model_copy(deep=True)
        provenance.executor = executor_config.model_copy(deep=True)
        spec = ExecutionRunSpec(
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
            executor_config=executor_config,
            model_config=payload.model_settings,
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
