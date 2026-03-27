from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.errors import AppError
from app.modules.runs.application.ports import (
    PublishedRunRuntimePort,
    RunRepository,
)
from app.modules.runs.application.results import PublishedRunExecutionResult
from app.modules.runs.application.telemetry import RunTelemetryIngestionService
from app.modules.runs.domain.models import ExecutionMetrics, RunSpec, RuntimeExecutionResult
from app.modules.runs.domain.policies import RunAggregate
from app.modules.shared.domain.enums import RunStatus, StepType
from app.modules.traces.domain.models import TraceIngestEvent


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
            prompt_version=str(payload.project_metadata.get("prompt_version", "v1")),
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
                tool_calls=sum(
                    1 for event in result.trace_events if event.step_type == StepType.TOOL
                ),
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
        if not result.trace_events:
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
                }
            )
            for event in result.trace_events
        ]

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
        )


class ExecutionRecorder:
    def __init__(
        self,
        run_repository: RunRepository,
        telemetry_ingestor: RunTelemetryIngestionService,
    ) -> None:
        self.run_repository = run_repository
        self.telemetry_ingestor = telemetry_ingestor

    def record(self, run_id: UUID, record: ProjectedExecutionRecord) -> None:
        for event in record.events:
            self.telemetry_ingestor.ingest(event)

        run = self.run_repository.get(run_id)
        if not run:
            return
        updated = RunAggregate.load(run).record_metrics(record.metrics)
        self.run_repository.save(updated)


class RunExecutionService:
    def __init__(
        self,
        run_repository: RunRepository,
        published_runtime: PublishedRunRuntimePort,
        telemetry_ingestor: RunTelemetryIngestionService,
        projector: RunExecutionProjector | None = None,
        recorder: ExecutionRecorder | None = None,
    ) -> None:
        self.run_repository = run_repository
        self.published_runtime = published_runtime
        self.projector = projector or RunExecutionProjector()
        self.recorder = recorder or ExecutionRecorder(
            run_repository=run_repository,
            telemetry_ingestor=telemetry_ingestor,
        )

    def execute_run(self, run_id: UUID, payload: RunSpec) -> None:
        if not self._set_status(run_id, RunStatus.RUNNING):
            return

        context = RunExecutionContext.from_spec(run_id, payload)

        try:
            result = self.published_runtime.execute_published(run_id, payload)
            self._update_run_execution_details(run_id, result.runtime_result)
            record = self.projector.project_runtime_success(context, result)
            self.recorder.record(run_id, record)
            trace_failure = failure_from_trace_events(record.events)
            if trace_failure is not None:
                self._record_failure(run_id, trace_failure)
                self._set_status(run_id, RunStatus.FAILED, reason=trace_failure.message)
                return
            self._set_status(run_id, RunStatus.SUCCEEDED)
        except Exception as exc:
            failure = normalize_run_failure(exc)
            self.recorder.record(run_id, self.projector.project_runtime_failure(context, failure))
            self._record_failure(run_id, failure)
            self._set_status(run_id, RunStatus.FAILED, reason=failure.message)

    def _set_status(
        self,
        run_id: UUID,
        status: RunStatus,
        reason: str | None = None,
    ) -> bool:
        run = self.run_repository.get(run_id)
        if not run:
            return False

        aggregate = RunAggregate.load(run)
        try:
            if status == RunStatus.RUNNING:
                updated = aggregate.mark_running()
            elif status == RunStatus.SUCCEEDED:
                updated = aggregate.mark_succeeded()
            elif status == RunStatus.FAILED:
                updated = aggregate.mark_failed(reason)
            else:
                raise ValueError(f"unsupported status transition target={status.value}")
        except ValueError:
            return False

        self.run_repository.save(updated)
        return True

    def _update_run_execution_details(
        self,
        run_id: UUID,
        runtime_result: RuntimeExecutionResult,
    ) -> None:
        run = self.run_repository.get(run_id)
        if not run:
            return
        aggregate = RunAggregate.load(run)
        aggregate.update_model(runtime_result.resolved_model)
        updated = aggregate.update_execution_runtime(
            execution_backend=runtime_result.execution_backend,
            container_image=runtime_result.container_image,
        )
        self.run_repository.save(updated)

    def _record_failure(self, run_id: UUID, failure: RunFailureDetails) -> None:
        run = self.run_repository.get(run_id)
        if not run:
            return
        updated = RunAggregate.load(run).record_failure(
            error_code=failure.code,
            error_message=failure.message,
        )
        self.run_repository.save(updated)
