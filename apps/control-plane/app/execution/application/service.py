from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from agent_atlas_contracts.runtime import TraceIngestEvent as ContractTraceIngestEvent

from app.core.errors import AppError
from app.execution.adapters.specs import execution_handoff_from_run_spec
from app.execution.application.ports import ExecutionOutcomeSinkPort
from app.modules.runs.application.ports import (
    ArtifactResolverPort,
    RunnerPort,
)
from app.modules.runs.application.results import (
    PublishedRunExecutionResult,
)
from app.modules.runs.domain.models import (
    ExecutionMetrics,
    RunSpec,
)
from app.modules.shared.domain.enums import RunStatus, StepType
from app.modules.shared.domain.models import TraceTelemetryMetadata
from app.modules.shared.domain.traces import TraceIngestEvent


@dataclass(frozen=True)
class RunExecutionContext:
    run_id: UUID
    payload: RunSpec
    image_digest: str
    prompt_version: str

    @classmethod
    def from_spec(cls, run_id: UUID, payload: RunSpec) -> RunExecutionContext:
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


@dataclass(frozen=True)
class ProjectedExecutionRecord:
    events: list[TraceIngestEvent]
    metrics: ExecutionMetrics


@dataclass(frozen=True)
class RunFailureDetails:
    code: str
    message: str


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
        if raw_code == "agent_load_failed":
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
        return TraceTelemetryMetadata(
            agent_id=context.payload.agent_id,
            framework=provenance.framework if provenance else None,
            framework_type=provenance.framework_type if provenance else None,
            framework_version=provenance.framework_version if provenance else None,
            artifact_ref=provenance.artifact_ref if provenance else None,
            image_ref=provenance.image_ref if provenance else None,
            runner_backend=provenance.runner_backend if provenance else None,
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
                                "framework": event.metadata.framework
                                or (
                                    context.payload.provenance.framework
                                    if context.payload.provenance
                                    else None
                                ),
                                "artifact_ref": event.metadata.artifact_ref
                                or (
                                    context.payload.provenance.artifact_ref
                                    if context.payload.provenance
                                    else None
                                ),
                                "image_ref": event.metadata.image_ref
                                or (
                                    context.payload.provenance.image_ref
                                    if context.payload.provenance
                                    else None
                                ),
                                "runner_backend": event.metadata.runner_backend
                                or (
                                    context.payload.provenance.runner_backend
                                    if context.payload.provenance
                                    else None
                                ),
                                "executor_backend": event.metadata.executor_backend
                                or (
                                    context.payload.provenance.executor_backend
                                    if context.payload.provenance
                                    else None
                                ),
                                "experiment_id": event.metadata.experiment_id
                                or context.payload.experiment_id,
                                "dataset_version_id": event.metadata.dataset_version_id
                                or context.payload.dataset_version_id,
                                "dataset_sample_id": event.metadata.dataset_sample_id
                                or context.payload.dataset_sample_id,
                                "prompt_version": event.metadata.prompt_version
                                or context.prompt_version,
                                "image_digest": event.metadata.image_digest
                                or runtime_result.container_image
                                or context.image_digest,
                            }
                        )
                        if event.metadata
                        else self._event_metadata(context).model_copy(
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

    def execute_run(self, run_id: UUID, payload: RunSpec) -> None:
        if not self.sink.transition_status(run_id, RunStatus.STARTING):
            return

        context = RunExecutionContext.from_spec(run_id, payload)

        try:
            artifact = self.artifact_resolver.resolve(payload)
            attempt = self.sink.load_attempt(run_id)
            handoff = execution_handoff_from_run_spec(
                run_id=run_id,
                payload=payload,
                artifact=artifact,
                runner_backend=self._runner_backend(payload),
                attempt=attempt.attempt,
                attempt_id=attempt.attempt_id,
            )
            self.sink.record_execution_handoff(run_id, handoff)
            if not self.sink.transition_status(run_id, RunStatus.RUNNING):
                self.sink.mark_cancelled_if_requested(run_id)
                return
            result = self.runner.execute(handoff)
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
            failure = normalize_run_failure(exc)
            self.recorder.record(run_id, self.projector.project_runtime_failure(context, failure))
            if self.sink.mark_cancelled_if_requested(run_id):
                return
            self.sink.record_failure(run_id, failure)
            self.sink.transition_status(run_id, RunStatus.FAILED, reason=failure.message)

    def _runner_backend(self, payload: RunSpec) -> str:
        if payload.provenance and payload.provenance.runner_backend:
            return payload.provenance.runner_backend
        return self.default_runner_backend


__all__ = [
    "ExecutionRecorder",
    "ProjectedExecutionRecord",
    "RunExecutionContext",
    "RunExecutionProjector",
    "RunExecutionService",
    "RunFailureDetails",
    "failure_from_trace_events",
    "normalize_run_failure",
]
