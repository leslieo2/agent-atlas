from __future__ import annotations

from app.core.errors import AgentFrameworkMismatchError, AgentLoadFailedError
from app.modules.agents.domain.models import PublishedAgent
from app.modules.execution.application.ports import ExecutionControlPort
from app.modules.runs.application.ports import RunRepository
from app.modules.runs.domain.models import RunCreateInput, RunRecord, RunSpec
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
    if provenance.trace_backend is None:
        provenance.trace_backend = "phoenix"
    return provenance


class RunSubmissionService:
    def __init__(
        self,
        run_repository: RunRepository,
        execution_control: ExecutionControlPort,
        default_trace_backend: str = "phoenix",
    ) -> None:
        self.run_repository = run_repository
        self.execution_control = execution_control
        self.default_trace_backend = default_trace_backend

    def submit(self, payload: RunCreateInput, agent: PublishedAgent) -> RunRecord:
        effective_agent = _resolve_submission_agent(agent)
        provenance = _resolved_submission_provenance(agent, effective_agent)
        provenance.experiment_id = payload.experiment_id
        provenance.dataset_version_id = payload.dataset_version_id
        provenance.dataset_sample_id = payload.dataset_sample_id
        provenance.trace_backend = self.default_trace_backend
        executor_config = payload.executor_config or ExecutorConfig(
            backend=payload.executor_backend
        )
        spec = RunSpec(
            experiment_id=payload.experiment_id,
            dataset_version_id=payload.dataset_version_id,
            project=payload.project,
            dataset=payload.dataset,
            dataset_sample_id=payload.dataset_sample_id,
            agent_id=payload.agent_id,
            model=effective_agent.default_model,
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
