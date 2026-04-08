from __future__ import annotations

from uuid import UUID

from agent_atlas_contracts.execution import (
    ExecutionArtifact,
    RunnerBootstrapPaths,
    RunnerRunSpec,
    TracingConfig,
    TracingExportConfig,
)

from app.core.config import settings
from app.modules.runs.domain.models import RunExecutionSpec


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
    payload: RunExecutionSpec,
    *,
    artifact: ExecutionArtifact,
    runner_backend: str,
    attempt: int = 1,
    attempt_id: UUID | None = None,
    bootstrap: RunnerBootstrapPaths | None = None,
) -> RunnerRunSpec:
    provenance = payload.provenance
    normalized_runner_backend = runner_backend.strip()
    if not normalized_runner_backend:
        raise ValueError("runner backend must be provided when building RunnerRunSpec")
    if artifact.framework is None or not artifact.framework.strip():
        raise ValueError("resolved execution artifact is missing framework")
    if artifact.entrypoint is None or not artifact.entrypoint.strip():
        raise ValueError("resolved execution artifact is missing entrypoint")
    if not artifact.published_agent_snapshot:
        raise ValueError("resolved execution artifact is missing published agent snapshot")
    executor_config = payload.executor_config.model_dump(mode="json")
    execution_binding = payload.execution_binding or payload.executor_config.execution_binding
    if execution_binding is not None:
        executor_config["binding"] = execution_binding.model_dump(mode="json", exclude_none=True)
    return RunnerRunSpec(
        run_id=payload.run_id,
        runner_backend=normalized_runner_backend,
        experiment_id=payload.experiment_id,
        dataset_version_id=payload.dataset_version_id,
        dataset_sample_id=payload.dataset_sample_id,
        attempt=attempt,
        attempt_id=attempt_id,
        project=payload.project,
        dataset=payload.dataset,
        agent_id=payload.agent_id,
        model=payload.model,
        entrypoint=artifact.entrypoint,
        agent_type=payload.agent_type.value,
        prompt=payload.prompt,
        tags=list(payload.tags),
        project_metadata=dict(payload.project_metadata),
        execution_target=(
            payload.execution_target.model_copy(deep=True)
            if payload.execution_target is not None
            else None
        ),
        executor_config=executor_config,
        agent_family=provenance.agent_family if provenance is not None else None,
        framework=artifact.framework,
        framework_type=provenance.agent_family if provenance is not None else None,
        artifact_ref=artifact.artifact_ref,
        image_ref=artifact.image_ref,
        trace_backend=provenance.trace_backend if provenance is not None else None,
        tracing=_runner_tracing_config(
            provenance.trace_backend if provenance is not None else None
        ),
        published_agent_snapshot=dict(artifact.published_agent_snapshot),
        bootstrap=bootstrap or RunnerBootstrapPaths(),
    )
