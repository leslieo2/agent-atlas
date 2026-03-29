from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from app.core.errors import AgentLoadFailedError, UnsupportedOperationError
from app.modules.agents.domain.models import PublishedAgent
from app.modules.runs.application.ports import PublishedRunRuntimePort
from app.modules.runs.application.results import RunnerExecutionResult
from app.modules.runs.domain.models import (
    ResolvedRunArtifact,
    RunnerExecutionHandoff,
    RunSpec,
)


class _RunnerExecutor(Protocol):
    def execute(self, handoff: RunnerExecutionHandoff) -> RunnerExecutionResult: ...


class PublishedArtifactResolver:
    def resolve(self, payload: RunSpec) -> ResolvedRunArtifact:
        provenance = payload.provenance
        if provenance is None or provenance.published_agent_snapshot is None:
            raise AgentLoadFailedError(
                "run payload is missing a published agent snapshot",
                agent_id=payload.agent_id,
            )

        snapshot = provenance.published_agent_snapshot
        try:
            published_agent = PublishedAgent.model_validate(snapshot)
        except Exception as exc:
            raise AgentLoadFailedError(
                "published agent snapshot is missing manifest metadata",
                agent_id=payload.agent_id,
            ) from exc

        manifest = snapshot.get("manifest")
        if not isinstance(manifest, dict):
            raise AgentLoadFailedError(
                "published agent snapshot is missing manifest metadata",
                agent_id=payload.agent_id,
            )
        runtime_artifact = published_agent.effective_runtime_artifact()
        framework = provenance.framework or runtime_artifact.framework
        entrypoint = runtime_artifact.entrypoint or published_agent.entrypoint or payload.entrypoint
        artifact_ref = provenance.artifact_ref or runtime_artifact.artifact_ref
        image_ref = provenance.image_ref or runtime_artifact.image_ref
        source_fingerprint = runtime_artifact.source_fingerprint
        if artifact_ref is None and image_ref is None:
            raise AgentLoadFailedError(
                "published agent snapshot is missing runtime artifact metadata",
                agent_id=payload.agent_id,
                framework=framework or "unknown",
            )

        return ResolvedRunArtifact(
            framework=framework,
            entrypoint=entrypoint,
            source_fingerprint=source_fingerprint,
            artifact_ref=artifact_ref,
            image_ref=image_ref,
            published_agent_snapshot=published_agent.to_snapshot(),
        )


class LocalProcessRunner:
    def __init__(
        self,
        published_runtime: PublishedRunRuntimePort,
    ) -> None:
        self.published_runtime = published_runtime

    @staticmethod
    def backend_name() -> str:
        return "local-process"

    def execute(self, handoff: RunnerExecutionHandoff) -> RunnerExecutionResult:
        execution = self.published_runtime.execute_published(
            handoff.run_id,
            handoff.to_run_spec(),
        )
        return RunnerExecutionResult(
            runner_backend=self.backend_name(),
            artifact_ref=handoff.artifact_ref,
            image_ref=handoff.image_ref,
            execution=execution,
        )


class RunnerRegistry:
    def __init__(
        self,
        *,
        runners: Mapping[str, _RunnerExecutor],
        default_backend: str,
    ) -> None:
        self.runners = {key.strip().lower(): value for key, value in runners.items()}
        self.default_backend = default_backend.strip().lower()
        if self.default_backend not in self.runners:
            raise ValueError(f"unsupported default runner backend '{default_backend}'")

    def execute(self, handoff: RunnerExecutionHandoff) -> RunnerExecutionResult:
        backend = handoff.runner_backend.strip().lower()
        runner = self.runners.get(backend)
        if runner is None:
            raise UnsupportedOperationError(
                f"runner backend '{handoff.runner_backend}' is not configured",
                runner_backend=handoff.runner_backend,
            )
        return runner.execute(handoff)
