from __future__ import annotations

from uuid import UUID

from agent_atlas_contracts.execution import (
    ExecutionArtifact,
    ExecutionHandoff,
    RunnerBootstrapPaths,
    RunnerRunSpec,
    TracingConfig,
    TracingExportConfig,
)

from app.core.config import settings
from app.modules.runs.domain.models import RunSpec


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
        tracing=_runner_tracing_config(
            provenance.trace_backend if provenance is not None else None
        ),
        published_agent_snapshot=published_agent_snapshot,
        bootstrap=bootstrap or RunnerBootstrapPaths(),
    )


def execution_handoff_from_run_spec(
    *,
    run_id: UUID,
    payload: RunSpec,
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
        input_summary=handoff.input_summary,
        prompt=handoff.prompt,
        tags=list(handoff.tags),
        project_metadata=dict(handoff.project_metadata),
        model_settings=dict(handoff.model_settings) if handoff.model_settings is not None else None,
        prompt_config=dict(handoff.prompt_config) if handoff.prompt_config is not None else None,
        toolset_config=dict(handoff.toolset_config),
        evaluator_config=dict(handoff.evaluator_config),
        executor_config=dict(handoff.executor_config),
        approval_policy=(
            dict(handoff.approval_policy) if handoff.approval_policy is not None else None
        ),
        framework=handoff.framework,
        framework_type=handoff.framework_type,
        framework_version=handoff.framework_version,
        artifact_ref=handoff.artifact_ref,
        image_ref=handoff.image_ref,
        trace_backend=handoff.trace_backend,
        tracing=_runner_tracing_config(handoff.trace_backend),
        published_agent_snapshot=handoff.published_agent_snapshot,
    )


__all__ = [
    "execution_handoff_from_run_spec",
    "runner_run_spec_from_handoff",
    "runner_run_spec_from_run_spec",
]
