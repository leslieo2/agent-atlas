from __future__ import annotations

from uuid import UUID

from agent_atlas_contracts.execution import RunnerBootstrapPaths, RunnerRunSpec

from app.modules.runs.domain.models import RunnerExecutionHandoff, RunSpec


def runner_run_spec_from_run_spec(
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


def runner_run_spec_from_handoff(handoff: RunnerExecutionHandoff) -> RunnerRunSpec:
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


__all__ = [
    "runner_run_spec_from_handoff",
    "runner_run_spec_from_run_spec",
]
