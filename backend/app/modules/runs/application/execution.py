from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.runs.application.ports import (
    RunnerRegistryPort,
    RunRepository,
    TraceIngestionPort,
)
from app.modules.runs.domain.models import (
    ExecutionMetrics,
    RunSpec,
    RuntimeExecutionResult,
)
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
    event: TraceIngestEvent
    metrics: ExecutionMetrics


class RunExecutionProjector:
    @staticmethod
    def planner_span_id(run_id: UUID) -> str:
        return f"span-{run_id}-1"

    @staticmethod
    def runtime_preamble_span_id(run_id: UUID) -> str:
        return f"span-{run_id}-2"

    @staticmethod
    def runtime_result_span_id(run_id: UUID) -> str:
        return f"span-{run_id}-3"

    @staticmethod
    def persistence_span_id(run_id: UUID) -> str:
        return f"span-{run_id}-4"

    def project_planner(self, context: RunExecutionContext) -> ProjectedExecutionRecord:
        prompt = (
            f"Plan execution flow for dataset {context.payload.dataset} "
            f"using adapter {context.payload.agent_type.value}."
        )
        output = f"Single-step live model execution planned for project {context.payload.project}."
        return ProjectedExecutionRecord(
            event=self._build_event(
                context=context,
                span_id=self.planner_span_id(context.run_id),
                parent_span_id=None,
                step_type=StepType.PLANNER,
                name="planner-v1",
                input_payload={
                    "prompt": prompt,
                    "agent_type": context.payload.agent_type.value,
                    "model": "planner-v1",
                    "temperature": 0.0,
                },
                output_payload={"output": output, "success": True},
                latency_ms=1,
                token_usage=0,
            ),
            metrics=ExecutionMetrics(latency_ms=1, token_cost=0),
        )

    def project_runtime_preamble(self, context: RunExecutionContext) -> ProjectedExecutionRecord:
        return ProjectedExecutionRecord(
            event=self._build_event(
                context=context,
                span_id=self.runtime_preamble_span_id(context.run_id),
                parent_span_id=self.planner_span_id(context.run_id),
                step_type=StepType.TOOL,
                name="runtime-context",
                input_payload={
                    "prompt": "Prepare runtime context for execution",
                    "type": "preamble",
                    "model": "planner-v1",
                    "temperature": 0.0,
                },
                output_payload={"output": "runtime context prepared", "success": True},
                latency_ms=2,
                token_usage=0,
                tool_name="runtime-context",
            ),
            metrics=ExecutionMetrics(
                latency_ms=2,
                token_cost=0,
                tool_calls=1,
            ),
        )

    def project_runtime_success(
        self,
        context: RunExecutionContext,
        result: RuntimeExecutionResult,
    ) -> ProjectedExecutionRecord:
        return ProjectedExecutionRecord(
            event=self._build_event(
                context=context,
                span_id=self.runtime_result_span_id(context.run_id),
                parent_span_id=self.runtime_preamble_span_id(context.run_id),
                step_type=StepType.LLM,
                name=context.payload.model,
                input_payload={
                    "prompt": context.payload.prompt,
                    "model": context.payload.model,
                    "temperature": 0.0,
                },
                output_payload={
                    "output": result.output,
                    "success": True,
                    "provider": result.provider,
                },
                latency_ms=result.latency_ms,
                token_usage=result.token_usage,
                image_digest=result.container_image or context.image_digest,
            ),
            metrics=ExecutionMetrics(
                latency_ms=result.latency_ms,
                token_cost=result.token_usage,
            ),
        )

    def project_runtime_failure(
        self,
        context: RunExecutionContext,
        error: str,
    ) -> ProjectedExecutionRecord:
        output = f"live execution failed: {error}"
        return ProjectedExecutionRecord(
            event=self._build_event(
                context=context,
                span_id=self.runtime_result_span_id(context.run_id),
                parent_span_id=self.runtime_preamble_span_id(context.run_id),
                step_type=StepType.LLM,
                name=context.payload.model,
                input_payload={
                    "prompt": context.payload.prompt,
                    "model": context.payload.model,
                    "temperature": 0.0,
                },
                output_payload={"output": output, "success": False, "error": error},
                latency_ms=0,
                token_usage=0,
            ),
            metrics=ExecutionMetrics(),
        )

    def project_persistence(self, context: RunExecutionContext) -> ProjectedExecutionRecord:
        return ProjectedExecutionRecord(
            event=self._build_event(
                context=context,
                span_id=self.persistence_span_id(context.run_id),
                parent_span_id=self.runtime_result_span_id(context.run_id),
                step_type=StepType.MEMORY,
                name="recorder",
                input_payload={
                    "prompt": "Persist normalized artifacts",
                    "result": "persist",
                    "model": "recorder",
                    "temperature": 0.0,
                },
                output_payload={"output": "trajectory and spans persisted", "success": True},
                latency_ms=1,
                token_usage=0,
            ),
            metrics=ExecutionMetrics(latency_ms=1, token_cost=0),
        )

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
        trace_ingestor: TraceIngestionPort,
    ) -> None:
        self.run_repository = run_repository
        self.trace_ingestor = trace_ingestor

    def record(self, run_id: UUID, record: ProjectedExecutionRecord) -> None:
        self.trace_ingestor.ingest(record.event)

        run = self.run_repository.get(run_id)
        if not run:
            return
        updated = RunAggregate.load(run).record_metrics(record.metrics)
        self.run_repository.save(updated)


class RunExecutionService:
    def __init__(
        self,
        run_repository: RunRepository,
        runner_registry: RunnerRegistryPort,
        trace_ingestor: TraceIngestionPort,
        projector: RunExecutionProjector | None = None,
        recorder: ExecutionRecorder | None = None,
    ) -> None:
        self.run_repository = run_repository
        self.runner_registry = runner_registry
        self.projector = projector or RunExecutionProjector()
        self.recorder = recorder or ExecutionRecorder(
            run_repository=run_repository,
            trace_ingestor=trace_ingestor,
        )

    def execute_run(self, run_id: UUID, payload: RunSpec) -> None:
        if not self._set_status(run_id, RunStatus.RUNNING):
            return

        context = RunExecutionContext.from_spec(run_id, payload)
        self.recorder.record(run_id, self.projector.project_planner(context))
        self.recorder.record(run_id, self.projector.project_runtime_preamble(context))

        try:
            runner = self.runner_registry.get_runner(payload.agent_type)
            result = runner.execute(payload.agent_type, payload.model, payload.prompt)
            self.recorder.record(run_id, self.projector.project_runtime_success(context, result))
            self._set_status(run_id, RunStatus.SUCCEEDED)
        except Exception as exc:
            self.recorder.record(run_id, self.projector.project_runtime_failure(context, str(exc)))
            self._set_status(run_id, RunStatus.FAILED, reason=str(exc))

        self.recorder.record(run_id, self.projector.project_persistence(context))

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
