from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - runner invocation is a controlled local module entrypoint
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol

from agent_atlas_contracts.execution import (
    ArtifactManifest,
    EventEnvelope,
    ExecutionArtifact,
    ExecutionHandoff,
    TerminalResult,
)
from agent_atlas_contracts.runtime import PublishedRunExecutionResult, RuntimeExecutionResult

from app.core.errors import (
    AgentFrameworkMismatchError,
    AgentLoadFailedError,
    AgentNotPublishedError,
    AgentValidationFailedError,
    AppError,
    DatasetNotFoundError,
    ModelNotFoundError,
    ProviderAuthError,
    ProviderTimeoutError,
    PublishedAgentNotFoundError,
    RateLimitedError,
    UnsupportedAdapterError,
    UnsupportedOperationError,
)
from app.execution.adapters.launchers import LocalLauncher
from app.execution.application.ports import PublishedRunRuntimePort
from app.execution.application.results import RunnerExecutionResult
from app.execution.contracts import ExecutionRunSpec, runner_run_spec_from_handoff
from app.modules.agents.domain.models import PublishedAgent


class _RunnerExecutor(Protocol):
    def execute(self, handoff: ExecutionHandoff) -> RunnerExecutionResult: ...


class SerializedSubprocessAppError(AppError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        context: Mapping[str, str] | None = None,
    ) -> None:
        self.code = code
        super().__init__(message, **dict(context or {}))


class PublishedArtifactResolver:
    def resolve(self, payload: ExecutionRunSpec) -> ExecutionArtifact:
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

        return ExecutionArtifact(
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
        launcher: LocalLauncher | None = None,
        *,
        published_runtime: PublishedRunRuntimePort | None = None,
        command: Sequence[str] | None = None,
        process_cwd: Path | None = None,
    ) -> None:
        self.launcher = launcher or LocalLauncher()
        self.published_runtime = published_runtime
        self.command = list(command) if command is not None else self.default_command()
        self.process_cwd = process_cwd or Path(__file__).resolve().parents[3]

    @staticmethod
    def backend_name() -> str:
        return "local-process"

    @staticmethod
    def default_command() -> list[str]:
        return [sys.executable, "-m", "app.execution.runner_process"]

    def execute(self, handoff: ExecutionHandoff) -> RunnerExecutionResult:
        runner_payload = runner_run_spec_from_handoff(handoff)
        session = self.launcher.prepare(runner_payload)
        if self._use_in_process_runtime(session.payload.executor_config):
            if self.published_runtime is None:
                raise RuntimeError("published runtime is not configured")
            execution = self.published_runtime.execute_published(
                handoff.run_id,
                session.payload,
            )
            self.launcher.persist_result(session, execution)
            return RunnerExecutionResult(
                runner_backend=self.backend_name(),
                artifact_ref=handoff.artifact_ref,
                image_ref=handoff.image_ref,
                execution=execution,
            )

        # The command is fixed to a local Python module entrypoint and receives only
        # launcher-generated bootstrap file paths, not user-provided shell fragments.
        completed = subprocess.run(  # nosec B603
            [*self.command, *session.entrypoint_args],
            cwd=self.process_cwd,
            env={**os.environ, **session.environment},
            capture_output=True,
            text=True,
            check=False,
        )
        terminal_result = _load_terminal_result(session)
        if completed.returncode != 0 or (
            terminal_result is not None and terminal_result.status != "succeeded"
        ):
            _raise_runner_failure(
                terminal_result=terminal_result,
                stderr=completed.stderr,
                stdout=completed.stdout,
                model=handoff.model,
            )

        execution = _load_published_execution_result(session)
        return RunnerExecutionResult(
            runner_backend=self.backend_name(),
            artifact_ref=handoff.artifact_ref,
            image_ref=handoff.image_ref,
            execution=execution,
        )

    @staticmethod
    def _use_in_process_runtime(executor_config: Mapping[str, object]) -> bool:
        mode = executor_config.get("runner_mode")
        if not isinstance(mode, str):
            metadata = executor_config.get("metadata")
            if isinstance(metadata, Mapping):
                metadata_mode = metadata.get("runner_mode")
                mode = metadata_mode if isinstance(metadata_mode, str) else None
        return isinstance(mode, str) and mode.strip().lower() == "in-process"


def _load_published_execution_result(session) -> PublishedRunExecutionResult:
    events_path = Path(session.payload.bootstrap.events_path)
    runtime_result = _load_runtime_result(session)
    artifact_manifest_path = Path(session.payload.bootstrap.artifact_manifest_path)
    terminal_result = _load_terminal_result(session)
    if terminal_result is None:
        raise RuntimeError("runner subprocess did not produce a terminal result")
    if runtime_result is None:
        runtime_result = RuntimeExecutionResult(
            output=terminal_result.output or "",
            latency_ms=terminal_result.metrics.latency_ms,
            token_usage=terminal_result.metrics.token_usage,
            provider=terminal_result.producer.runtime or "local-subprocess",
            resolved_model=session.payload.model,
        )

    event_envelopes: list[EventEnvelope] = []
    if events_path.exists():
        lines = [
            line.strip()
            for line in events_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        event_envelopes = [EventEnvelope.model_validate(json.loads(line)) for line in lines]

    artifact_manifest = None
    if artifact_manifest_path.exists():
        artifact_manifest = ArtifactManifest.model_validate_json(
            artifact_manifest_path.read_text(encoding="utf-8")
        )

    return PublishedRunExecutionResult(
        runtime_result=runtime_result,
        event_envelopes=event_envelopes,
        terminal_result=terminal_result,
        artifact_manifest=artifact_manifest,
    )


def _load_runtime_result(session) -> RuntimeExecutionResult | None:
    runtime_result_path = Path(session.payload.bootstrap.runtime_result_path)
    if not runtime_result_path.exists():
        return None
    return RuntimeExecutionResult.model_validate_json(
        runtime_result_path.read_text(encoding="utf-8")
    )


def _load_terminal_result(session) -> TerminalResult | None:
    terminal_result_path = Path(session.payload.bootstrap.terminal_result_path)
    if not terminal_result_path.exists():
        return None
    return TerminalResult.model_validate_json(terminal_result_path.read_text(encoding="utf-8"))


def _raise_runner_failure(
    *,
    terminal_result: TerminalResult | None,
    stderr: str,
    stdout: str,
    model: str,
) -> None:
    if terminal_result is not None:
        serialized_error = _deserialize_app_error(
            terminal_result=terminal_result,
            model=model,
        )
        if serialized_error is not None:
            raise serialized_error

        raise RuntimeError(
            terminal_result.reason_message or terminal_result.output or "runner subprocess failed"
        )

    message = stderr.strip() or stdout.strip() or "runner subprocess failed"
    raise RuntimeError(message)


def _deserialize_app_error(
    *,
    terminal_result: TerminalResult,
    model: str,
) -> AppError | None:
    reason_message = (
        terminal_result.reason_message or terminal_result.output or "runner subprocess failed"
    )
    reason_code = terminal_result.reason_code or "runner_subprocess_failed"
    context = dict(terminal_result.reason_context)
    if reason_code == ModelNotFoundError.code:
        return ModelNotFoundError(
            model=context.get("model") or model,
            message=reason_message,
        )
    if reason_code == ProviderAuthError.code:
        return ProviderAuthError(reason_message)
    if reason_code == RateLimitedError.code:
        return RateLimitedError(reason_message)
    if reason_code == ProviderTimeoutError.code:
        return ProviderTimeoutError(reason_message)
    if reason_code == AgentFrameworkMismatchError.code:
        return AgentFrameworkMismatchError(
            reason_message,
            agent_id=context.get("agent_id") or "unknown",
            expected_framework=context.get("expected_framework"),
            actual_framework=context.get("actual_framework"),
            actual_agent_type=context.get("actual_agent_type"),
            snapshot_agent_id=context.get("snapshot_agent_id"),
        )
    if reason_code == AgentLoadFailedError.code:
        return AgentLoadFailedError(reason_message, **context)
    if reason_code == UnsupportedAdapterError.code:
        return UnsupportedAdapterError(reason_message)
    if reason_code == UnsupportedOperationError.code:
        return UnsupportedOperationError(reason_message, **context)
    if reason_code == AgentNotPublishedError.code:
        agent_id = context.get("agent_id")
        if agent_id:
            return AgentNotPublishedError(agent_id=agent_id)
        return AgentNotPublishedError(agent_id="unknown")
    if reason_code == PublishedAgentNotFoundError.code:
        agent_id = context.get("agent_id")
        if agent_id:
            return PublishedAgentNotFoundError(agent_id=agent_id)
        return PublishedAgentNotFoundError(agent_id="unknown")
    if reason_code == AgentValidationFailedError.code:
        agent_id = context.get("agent_id")
        if agent_id:
            return AgentValidationFailedError(agent_id=agent_id, message=reason_message)
        return AgentValidationFailedError(agent_id="unknown", message=reason_message)
    if reason_code == DatasetNotFoundError.code:
        dataset = context.get("dataset")
        if dataset:
            return DatasetNotFoundError(dataset=dataset)
        return DatasetNotFoundError(dataset="unknown")
    if reason_code != "runner_subprocess_failed":
        return SerializedSubprocessAppError(
            code=reason_code,
            message=reason_message,
            context=context,
        )
    return None


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

    def execute(self, handoff: ExecutionHandoff) -> RunnerExecutionResult:
        backend = handoff.runner_backend.strip().lower()
        runner = self.runners.get(backend)
        if runner is None:
            raise UnsupportedOperationError(
                f"runner backend '{handoff.runner_backend}' is not configured",
                runner_backend=handoff.runner_backend,
            )
        return runner.execute(handoff)


__all__ = [
    "LocalProcessRunner",
    "PublishedArtifactResolver",
    "RunnerRegistry",
]
