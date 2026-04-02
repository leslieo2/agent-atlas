from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import UUID

from agent_atlas_contracts.runtime import TraceIngestEvent as ContractTraceIngestEvent

from app.core.errors import AppError, UnsupportedOperationError
from app.execution.application.ports import (
    ArtifactResolverPort,
    ExecutionOutcomeSinkPort,
    RunnerPort,
)
from app.execution.application.results import (
    ExecutionCancelled,
    ExecutionMetrics,
    ProjectedExecutionRecord,
    PublishedRunExecutionResult,
    RunFailureDetails,
    RunnerSubmissionRecord,
)
from app.execution.contracts import ExecutionRunSpec, runner_run_spec_from_run_spec
from app.execution.metadata import requested_runner_backend, uses_k8s_runner_backend
from app.modules.shared.domain.enums import RunStatus, StepType
from app.modules.shared.domain.models import TraceTelemetryMetadata
from app.modules.shared.domain.traces import TraceIngestEvent


@dataclass(frozen=True)
class RunExecutionContext:
    run_id: UUID
    payload: ExecutionRunSpec
    image_digest: str
    prompt_version: str
    runner_submission: RunnerSubmissionRecord | None = None

    @classmethod
    def from_spec(cls, run_id: UUID, payload: ExecutionRunSpec) -> RunExecutionContext:
        return cls(
            run_id=run_id,
            payload=payload,
            image_digest=str(payload.project_metadata.get("image_digest", "sha256:dev")),
            prompt_version=str(
                payload.project_metadata.get(
                    "prompt_version",
                    payload.prompt_config.prompt_version if payload.prompt_config else "v1",
                )
            ),
        )

    def with_runner_submission(
        self,
        record: RunnerSubmissionRecord,
    ) -> RunExecutionContext:
        return replace(self, runner_submission=record)


def failure_from_trace_events(events: list[TraceIngestEvent]) -> RunFailureDetails | None:
    for event in events:
        success = event.output.get("success")
        if success is not False:
            continue

        message = event.output.get("error") or event.output.get("output")
        normalized_message = str(message).strip() if message is not None else ""
        if not normalized_message:
            normalized_message = "run execution failed"

        raw_code = event.output.get("error_code")
        if isinstance(raw_code, str) and raw_code.strip():
            code = raw_code.strip()
        elif event.step_type == StepType.TOOL:
            code = "tool_execution"
        else:
            code = "run_execution_failed"

        return RunFailureDetails(code=code, message=normalized_message)

    return None


def normalize_run_failure(exc: Exception) -> RunFailureDetails:
    if isinstance(exc, AppError):
        raw_code = exc.code
        normalized_code = "runner_bootstrap"
        if raw_code in {"agent_load_failed", "agent_framework_mismatch"}:
            normalized_code = "agent_load"
        elif raw_code in {"provider_auth_error", "rate_limited"}:
            normalized_code = "provider_call"
        elif raw_code == "provider_timeout":
            normalized_code = "timeout_or_termination"
        elif "tool" in raw_code:
            normalized_code = "tool_execution"
        return RunFailureDetails(code=normalized_code, message=exc.message)

    message = str(exc).strip() or "run execution failed"
    return RunFailureDetails(code="run_execution_failed", message=message)


class RunExecutionProjector:
    @staticmethod
    def _event_metadata(context: RunExecutionContext) -> TraceTelemetryMetadata:
        provenance = context.payload.provenance
        runner_submission = context.runner_submission
        return TraceTelemetryMetadata(
            agent_id=context.payload.agent_id,
            agent_family=(
                runner_submission.framework_type
                if runner_submission is not None and runner_submission.framework_type
                else provenance.agent_family
                if provenance
                else None
            ),
            framework=(
                runner_submission.framework
                if runner_submission is not None and runner_submission.framework
                else provenance.framework
                if provenance
                else None
            ),
            framework_type=(
                runner_submission.framework_type
                if runner_submission is not None and runner_submission.framework_type
                else provenance.agent_family
                if provenance
                else None
            ),
            framework_version=provenance.framework_version if provenance else None,
            artifact_ref=(
                runner_submission.artifact_ref
                if runner_submission is not None and runner_submission.artifact_ref is not None
                else provenance.artifact_ref
                if provenance
                else None
            ),
            image_ref=(
                runner_submission.image_ref
                if runner_submission is not None and runner_submission.image_ref is not None
                else provenance.image_ref
                if provenance
                else None
            ),
            runner_backend=(
                runner_submission.runner_backend
                if runner_submission is not None
                else provenance.runner_backend
                if provenance
                else None
            ),
            executor_backend=provenance.executor_backend if provenance else None,
            experiment_id=context.payload.experiment_id,
            dataset_version_id=context.payload.dataset_version_id,
            dataset_sample_id=context.payload.dataset_sample_id,
            prompt_version=context.prompt_version,
            image_digest=context.image_digest,
        )

    @staticmethod
    def runtime_result_span_id(run_id: UUID) -> str:
        return f"span-{run_id}-1"

    def project_runtime_success(
        self,
        context: RunExecutionContext,
        result: PublishedRunExecutionResult,
    ) -> ProjectedExecutionRecord:
        events = self._project_trace_events(context=context, result=result)
        runtime_result = result.runtime_result
        return ProjectedExecutionRecord(
            events=events,
            metrics=ExecutionMetrics(
                latency_ms=runtime_result.latency_ms,
                token_cost=runtime_result.token_usage,
                tool_calls=sum(1 for event in events if event.step_type == StepType.TOOL),
            ),
        )

    def project_runtime_failure(
        self,
        context: RunExecutionContext,
        error: RunFailureDetails,
    ) -> ProjectedExecutionRecord:
        output = f"live execution failed: {error.message}"
        return ProjectedExecutionRecord(
            events=[
                self._build_event(
                    context=context,
                    span_id=self.runtime_result_span_id(context.run_id),
                    parent_span_id=None,
                    step_type=StepType.LLM,
                    name=context.payload.model,
                    input_payload={
                        "prompt": context.payload.prompt,
                        "model": context.payload.model,
                        "temperature": 0.0,
                    },
                    output_payload={
                        "output": output,
                        "success": False,
                        "error": error.message,
                        "error_code": error.code,
                    },
                    latency_ms=0,
                    token_usage=0,
                )
            ],
            metrics=ExecutionMetrics(),
        )

    def _project_trace_events(
        self,
        context: RunExecutionContext,
        result: PublishedRunExecutionResult,
    ) -> list[TraceIngestEvent]:
        runtime_result = result.runtime_result
        fallback_metadata = self._event_metadata(context)
        trace_events = [
            self._normalize_trace_event(event) for event in result.projected_trace_events()
        ]
        if not trace_events:
            return [
                self._build_event(
                    context=context,
                    span_id=self.runtime_result_span_id(context.run_id),
                    parent_span_id=None,
                    step_type=StepType.LLM,
                    name=runtime_result.resolved_model or context.payload.model,
                    input_payload={
                        "prompt": context.payload.prompt,
                        "model": runtime_result.resolved_model or context.payload.model,
                        "temperature": 0.0,
                    },
                    output_payload={
                        "output": runtime_result.output,
                        "success": True,
                        "provider": runtime_result.provider,
                    },
                    latency_ms=runtime_result.latency_ms,
                    token_usage=runtime_result.token_usage,
                    image_digest=runtime_result.container_image or context.image_digest,
                )
            ]

        return [
            event.model_copy(
                update={
                    "image_digest": event.image_digest
                    or runtime_result.container_image
                    or context.image_digest,
                    "prompt_version": event.prompt_version or context.prompt_version,
                    "metadata": (
                        event.metadata.model_copy(
                            update={
                                "agent_id": event.metadata.agent_id or context.payload.agent_id,
                                "framework": (
                                    event.metadata.framework or fallback_metadata.framework
                                ),
                                "artifact_ref": (
                                    event.metadata.artifact_ref or fallback_metadata.artifact_ref
                                ),
                                "image_ref": (
                                    event.metadata.image_ref or fallback_metadata.image_ref
                                ),
                                "runner_backend": (
                                    event.metadata.runner_backend
                                    or fallback_metadata.runner_backend
                                ),
                                "executor_backend": (
                                    event.metadata.executor_backend
                                    or fallback_metadata.executor_backend
                                ),
                                "experiment_id": (
                                    event.metadata.experiment_id or fallback_metadata.experiment_id
                                ),
                                "dataset_version_id": (
                                    event.metadata.dataset_version_id
                                    or fallback_metadata.dataset_version_id
                                ),
                                "dataset_sample_id": (
                                    event.metadata.dataset_sample_id
                                    or fallback_metadata.dataset_sample_id
                                ),
                                "prompt_version": event.metadata.prompt_version
                                or context.prompt_version,
                                "image_digest": event.metadata.image_digest
                                or runtime_result.container_image
                                or context.image_digest,
                            }
                        )
                        if event.metadata
                        else fallback_metadata.model_copy(
                            update={
                                "image_digest": runtime_result.container_image
                                or context.image_digest,
                            }
                        )
                    ),
                }
            )
            for event in trace_events
        ]

    @staticmethod
    def _normalize_trace_event(
        event: ContractTraceIngestEvent | TraceIngestEvent,
    ) -> TraceIngestEvent:
        if isinstance(event, TraceIngestEvent):
            return event
        return TraceIngestEvent.model_validate(event.model_dump(mode="json"))

    def _build_event(
        self,
        context: RunExecutionContext,
        span_id: str,
        parent_span_id: str | None,
        step_type: StepType,
        name: str,
        input_payload: dict[str, object],
        output_payload: dict[str, object],
        latency_ms: int,
        token_usage: int,
        image_digest: str | None = None,
        tool_name: str | None = None,
    ) -> TraceIngestEvent:
        return TraceIngestEvent(
            run_id=context.run_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            step_type=step_type,
            name=name,
            input=input_payload,
            output=output_payload,
            tool_name=tool_name,
            latency_ms=latency_ms,
            token_usage=token_usage,
            image_digest=image_digest or context.image_digest,
            prompt_version=context.prompt_version,
            metadata=self._event_metadata(context).model_copy(
                update={
                    "image_digest": image_digest or context.image_digest,
                }
            ),
        )


class ExecutionRecorder:
    def __init__(
        self,
        sink: ExecutionOutcomeSinkPort,
    ) -> None:
        self.sink = sink

    def record(self, run_id: UUID, record: ProjectedExecutionRecord) -> None:
        self.sink.record_projected_execution(run_id, record)


class RunExecutionService:
    def __init__(
        self,
        artifact_resolver: ArtifactResolverPort,
        runner: RunnerPort,
        sink: ExecutionOutcomeSinkPort,
        default_runner_backend: str = "local-process",
        projector: RunExecutionProjector | None = None,
        recorder: ExecutionRecorder | None = None,
    ) -> None:
        self.artifact_resolver = artifact_resolver
        self.runner = runner
        self.sink = sink
        self.default_runner_backend = default_runner_backend
        self.projector = projector or RunExecutionProjector()
        self.recorder = recorder or ExecutionRecorder(sink=sink)

    def execute_run(self, run_id: UUID, payload: ExecutionRunSpec) -> None:
        normalized_payload = payload.model_copy(update={"run_id": run_id})
        if not self.sink.transition_status(run_id, RunStatus.STARTING):
            return

        context = RunExecutionContext.from_spec(run_id, normalized_payload)

        try:
            artifact = self.artifact_resolver.resolve(normalized_payload)
            attempt = self.sink.load_attempt(run_id)
            runner_payload = runner_run_spec_from_run_spec(
                payload=normalized_payload,
                artifact=artifact,
                runner_backend=self._runner_backend(normalized_payload),
                attempt=attempt.attempt,
                attempt_id=attempt.attempt_id,
            )
            runner_submission = RunnerSubmissionRecord(
                runner_backend=runner_payload.runner_backend,
                framework_type=runner_payload.framework_type,
                framework=runner_payload.framework,
                artifact_ref=runner_payload.artifact_ref,
                image_ref=runner_payload.image_ref,
            )
            context = context.with_runner_submission(runner_submission)
            self.sink.record_runner_submission(
                run_id,
                runner_submission,
            )
            if not self.sink.transition_status(run_id, RunStatus.RUNNING):
                self.sink.mark_cancelled_if_requested(run_id)
                return
            result = self.runner.execute(runner_payload)
            self.sink.record_runner_result(run_id, result)
            record = self.projector.project_runtime_success(context, result.execution)
            self.recorder.record(run_id, record)
            if self.sink.mark_cancelled_if_requested(run_id):
                return
            trace_failure = failure_from_trace_events(record.events)
            if trace_failure is not None:
                self.sink.record_failure(run_id, trace_failure)
                self.sink.transition_status(run_id, RunStatus.FAILED, reason=trace_failure.message)
                return
            self.sink.transition_status(run_id, RunStatus.SUCCEEDED)
        except Exception as exc:
            if isinstance(exc, ExecutionCancelled):
                self.sink.mark_cancelled_if_requested(run_id)
                return
            failure = normalize_run_failure(exc)
            self.recorder.record(run_id, self.projector.project_runtime_failure(context, failure))
            if self.sink.mark_cancelled_if_requested(run_id):
                return
            self.sink.record_failure(run_id, failure)
            self.sink.transition_status(run_id, RunStatus.FAILED, reason=failure.message)

    def _runner_backend(self, payload: ExecutionRunSpec) -> str:
        execution_backend = payload.executor_config.backend.strip().lower()
        if execution_backend == "external-runner":
            if uses_k8s_runner_backend(payload.executor_config):
                return "k8s-container"
            configured_runner_backend = requested_runner_backend(payload.executor_config)
            if configured_runner_backend is not None:
                return configured_runner_backend
            return self.default_runner_backend
        if execution_backend == "k8s-job":
            return "k8s-container"
        if execution_backend == "local-runner":
            return "local-process"
        raise UnsupportedOperationError(
            (
                f"execution backend '{payload.executor_config.backend}' "
                "cannot resolve a runner backend"
            ),
            executor_backend=payload.executor_config.backend,
        )


__all__ = [
    "ExecutionRecorder",
    "RunExecutionContext",
    "RunExecutionProjector",
    "RunExecutionService",
    "failure_from_trace_events",
    "normalize_run_failure",
]
