from __future__ import annotations

from uuid import uuid4

from app.core.errors import ProviderAuthError
from app.infrastructure.adapters.trace_backend import AtlasStateTraceBackend
from app.infrastructure.adapters.trace_projection import TraceIngestProjector
from app.infrastructure.adapters.trajectory_projection import TraceEventTrajectoryProjector
from app.infrastructure.repositories import (
    StateRunRepository,
    StateTraceRepository,
    StateTrajectoryRepository,
)
from app.modules.runs.application.execution import (
    ExecutionRecorder,
    RunExecutionContext,
    RunExecutionProjector,
)
from app.modules.runs.application.results import (
    PublishedRunExecutionResult,
    RunnerExecutionResult,
)
from app.modules.runs.application.telemetry import (
    RunTelemetryIngestionService,
    TrajectoryRecorder,
)
from app.modules.runs.domain.models import (
    ResolvedRunArtifact,
    RunRecord,
    RunSpec,
    RuntimeExecutionResult,
)
from app.modules.shared.domain.enums import AdapterKind, RunStatus, StepType
from app.modules.traces.application.use_cases import (
    TraceCommands,
    TraceIngestionWorkflow,
    TraceRecorder,
)
from app.modules.traces.domain.models import TraceIngestEvent


def _build_telemetry_ingestor(
    trace_repository: StateTraceRepository,
    trajectory_repository: StateTrajectoryRepository,
) -> RunTelemetryIngestionService:
    return RunTelemetryIngestionService(
        trace_ingestor=TraceCommands(
            workflow=TraceIngestionWorkflow(
                trace_projector=TraceIngestProjector(),
                trace_recorder=TraceRecorder(
                    trace_backend=AtlasStateTraceBackend(trace_repository),
                ),
            )
        ),
        trajectory_recorder=TrajectoryRecorder(
            trajectory_repository=trajectory_repository,
            step_projector=TraceEventTrajectoryProjector(),
        ),
    )


class _FixedArtifactResolver:
    def resolve(self, payload: RunSpec) -> ResolvedRunArtifact:
        entrypoint = payload.entrypoint or "app.agent_plugins.basic:build_agent"
        return ResolvedRunArtifact(
            framework=payload.agent_type.value,
            entrypoint=entrypoint,
            source_fingerprint="fingerprint-test",
            artifact_ref=f"source://{payload.agent_id or 'basic'}@fingerprint-test",
            image_ref=None,
            published_agent_snapshot={
                "manifest": {
                    "agent_id": payload.agent_id or "basic",
                    "name": "Basic",
                    "description": "Basic agent",
                    "framework": payload.agent_type.value,
                    "default_model": payload.model,
                    "tags": [],
                },
                "entrypoint": entrypoint,
                "published_at": "2026-03-20T09:00:00Z",
            },
        )


def test_run_execution_projector_builds_success_trace_event():
    run_id = uuid4()
    context = RunExecutionContext.from_spec(
        run_id,
        RunSpec(
            project="control-plane",
            dataset="crm-v2",
            model="gpt-5.4-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
            input_summary="projector test",
            prompt="Explain the plan.",
            project_metadata={"image_digest": "sha256:test", "prompt_version": "v2"},
        ),
    )
    projector = RunExecutionProjector()

    record = projector.project_runtime_success(
        context,
        PublishedRunExecutionResult(
            runtime_result=RuntimeExecutionResult(
                output="Projected success output",
                latency_ms=17,
                token_usage=31,
                provider="mock",
                execution_backend="local",
                container_image="python:3.12-slim",
            )
        ),
    )

    assert len(record.events) == 1
    assert record.events[0].span_id == f"span-{run_id}-1"
    assert record.events[0].parent_span_id is None
    assert record.events[0].output["output"] == "Projected success output"
    assert record.events[0].output["provider"] == "mock"
    assert record.events[0].image_digest == "python:3.12-slim"
    assert record.metrics.token_cost == 31


def test_execution_recorder_ingests_trace_into_step_span_and_metrics():
    run_id = uuid4()
    run_repository = StateRunRepository()
    trajectory_repository = StateTrajectoryRepository()
    trace_repository = StateTraceRepository()

    run_repository.save(
        RunRecord(
            run_id=run_id,
            input_summary="record metrics",
            project="control-plane",
            dataset="crm-v2",
            model="gpt-5.4-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
            status=RunStatus.RUNNING,
        )
    )

    context = RunExecutionContext.from_spec(
        run_id,
        RunSpec(
            project="control-plane",
            dataset="crm-v2",
            model="gpt-5.4-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
            input_summary="record metrics",
            prompt="Record this execution.",
        ),
    )
    projector = RunExecutionProjector()
    recorder = ExecutionRecorder(
        run_repository=run_repository,
        telemetry_ingestor=_build_telemetry_ingestor(
            trace_repository=trace_repository,
            trajectory_repository=trajectory_repository,
        ),
    )

    recorder.record(
        run_id,
        projector.project_runtime_success(
            context,
            PublishedRunExecutionResult(
                runtime_result=RuntimeExecutionResult(
                    output="ok",
                    latency_ms=9,
                    token_usage=13,
                    provider="mock",
                )
            ),
        ),
    )

    run = run_repository.get(run_id)
    steps = trajectory_repository.list_for_run(run_id)
    spans = trace_repository.list_for_run(run_id)

    assert run is not None
    assert run.latency_ms == 9
    assert run.token_cost == 13
    assert run.tool_calls == 0
    expected_span_ids = [f"span-{run_id}-1"]
    assert [step.id for step in steps] == expected_span_ids
    assert [step.parent_step_id for step in steps] == [None]
    assert [span.span_id for span in spans] == expected_span_ids


def test_execution_recorder_ingests_runtime_trace_events_and_tool_metrics():
    run_id = uuid4()
    run_repository = StateRunRepository()
    trajectory_repository = StateTrajectoryRepository()
    trace_repository = StateTraceRepository()

    run_repository.save(
        RunRecord(
            run_id=run_id,
            input_summary="record tool metrics",
            project="control-plane",
            dataset="crm-v2",
            model="gpt-5.4-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
            status=RunStatus.RUNNING,
        )
    )

    context = RunExecutionContext.from_spec(
        run_id,
        RunSpec(
            project="control-plane",
            dataset="crm-v2",
            model="gpt-5.4-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
            input_summary="record tool metrics",
            prompt="Use the tool before answering.",
        ),
    )
    projector = RunExecutionProjector()
    recorder = ExecutionRecorder(
        run_repository=run_repository,
        telemetry_ingestor=_build_telemetry_ingestor(
            trace_repository=trace_repository,
            trajectory_repository=trajectory_repository,
        ),
    )

    recorder.record(
        run_id,
        projector.project_runtime_success(
            context,
            PublishedRunExecutionResult(
                runtime_result=RuntimeExecutionResult(
                    output="done",
                    latency_ms=12,
                    token_usage=21,
                    provider="openai-agents-sdk",
                ),
                trace_events=[
                    TraceIngestEvent(
                        run_id=run_id,
                        span_id=f"span-{run_id}-1",
                        step_type=StepType.LLM,
                        name="gpt-5.4-mini",
                        input={"prompt": "Use the tool before answering.", "model": "gpt-5.4-mini"},
                        output={
                            "output": (
                                'tool_call: lookup_shipping_window({"order_reference":"A-1024"})'
                            )
                        },
                        token_usage=8,
                    ),
                    TraceIngestEvent(
                        run_id=run_id,
                        span_id=f"span-{run_id}-2",
                        parent_span_id=f"span-{run_id}-1",
                        step_type=StepType.TOOL,
                        name="lookup_shipping_window",
                        input={"prompt": '{"order_reference":"A-1024"}'},
                        output={"output": "eta_window=2 business days"},
                        tool_name="lookup_shipping_window",
                    ),
                    TraceIngestEvent(
                        run_id=run_id,
                        span_id=f"span-{run_id}-3",
                        parent_span_id=f"span-{run_id}-2",
                        step_type=StepType.LLM,
                        name="gpt-5.4-mini",
                        input={
                            "prompt": (
                                "Tool outputs:\n"
                                "lookup_shipping_window: eta_window=2 business days"
                            )
                        },
                        output={"output": "ETA is 2 business days."},
                        token_usage=13,
                    ),
                ],
            ),
        ),
    )

    run = run_repository.get(run_id)
    steps = trajectory_repository.list_for_run(run_id)

    assert run is not None
    assert run.latency_ms == 12
    assert run.token_cost == 21
    assert run.tool_calls == 1
    assert [step.step_type for step in steps] == [StepType.LLM, StepType.TOOL, StepType.LLM]
    assert [step.parent_step_id for step in steps] == [
        None,
        f"span-{run_id}-1",
        f"span-{run_id}-2",
    ]


def test_run_execution_service_records_structured_failure_details():
    run_id = uuid4()
    run_repository = StateRunRepository()
    trajectory_repository = StateTrajectoryRepository()
    trace_repository = StateTraceRepository()

    run_repository.save(
        RunRecord(
            run_id=run_id,
            input_summary="record failure",
            project="control-plane",
            dataset="crm-v2",
            agent_id="basic",
            model="gpt-5.4-mini",
            entrypoint="app.agent_plugins.basic:build_agent",
            agent_type=AdapterKind.OPENAI_AGENTS,
            status=RunStatus.QUEUED,
        )
    )

    class ExplodingPublishedRuntime:
        def execute(self, *_args, **_kwargs):
            raise ProviderAuthError("provider authentication failed")

    from app.modules.runs.application.execution import RunExecutionService

    service = RunExecutionService(
        run_repository=run_repository,
        artifact_resolver=_FixedArtifactResolver(),
        runner=ExplodingPublishedRuntime(),
        telemetry_ingestor=_build_telemetry_ingestor(
            trace_repository=trace_repository,
            trajectory_repository=trajectory_repository,
        ),
    )

    payload = RunSpec(
        project="control-plane",
        dataset="crm-v2",
        agent_id="basic",
        model="gpt-5.4-mini",
        entrypoint="app.agent_plugins.basic:build_agent",
        agent_type=AdapterKind.OPENAI_AGENTS,
        input_summary="record failure",
        prompt="Trigger a failure.",
    )

    service.execute_run(run_id, payload)

    run = run_repository.get(run_id)
    steps = trajectory_repository.list_for_run(run_id)

    assert run is not None
    assert run.status == RunStatus.FAILED
    assert run.entrypoint == "app.agent_plugins.basic:build_agent"
    assert run.runner_backend == "local-process"
    assert run.artifact_ref == "source://basic@fingerprint-test"
    assert run.error_code == "provider_call"
    assert run.error_message == "provider authentication failed"
    assert run.termination_reason == "provider authentication failed"
    assert len(steps) == 1
    assert steps[0].output == "live execution failed: provider authentication failed"


def test_run_execution_service_marks_failed_runs_from_failed_trace_events():
    run_id = uuid4()
    run_repository = StateRunRepository()
    trajectory_repository = StateTrajectoryRepository()
    trace_repository = StateTraceRepository()

    run_repository.save(
        RunRecord(
            run_id=run_id,
            input_summary="record tool failure trace",
            project="control-plane",
            dataset="fulfillment-eval-v1",
            agent_id="fulfillment_ops",
            model="gpt-5.4-mini",
            entrypoint="app.agent_plugins.fulfillment_ops:build_agent",
            agent_type=AdapterKind.OPENAI_AGENTS,
            status=RunStatus.QUEUED,
        )
    )

    class FailedToolPublishedRuntime:
        def execute(self, *_args, **_kwargs):
            return RunnerExecutionResult(
                runner_backend="local-process",
                artifact_ref="source://fulfillment_ops@fingerprint-test",
                image_ref=None,
                execution=PublishedRunExecutionResult(
                    runtime_result=RuntimeExecutionResult(
                        output="success",
                        latency_ms=15,
                        token_usage=18,
                        provider="openai-agents-sdk",
                        resolved_model="gpt-5.4-mini",
                    ),
                    trace_events=[
                        TraceIngestEvent(
                            run_id=run_id,
                            span_id=f"span-{run_id}-1",
                            step_type=StepType.LLM,
                            name="gpt-5.4-mini",
                            input={
                                "prompt": (
                                    "Order ORD-ERR-100 is delayed. "
                                    "Check status and decide the next action."
                                ),
                                "model": "gpt-5.4-mini",
                            },
                            output={
                                "output": (
                                    "tool_call: " 'lookup_order_status({"order_id":"ORD-ERR-100"})'
                                ),
                                "success": True,
                            },
                            token_usage=8,
                        ),
                        TraceIngestEvent(
                            run_id=run_id,
                            span_id=f"span-{run_id}-2",
                            parent_span_id=f"span-{run_id}-1",
                            step_type=StepType.TOOL,
                            name="lookup_order_status",
                            input={"prompt": '{"order_id":"ORD-ERR-100"}'},
                            output={
                                "output": (
                                    "An error occurred while running the tool. Please try again. "
                                    "Error: tool backend unavailable for order 'ORD-ERR-100'"
                                ),
                                "success": False,
                                "error": "tool backend unavailable for order 'ORD-ERR-100'",
                            },
                            tool_name="lookup_order_status",
                        ),
                        TraceIngestEvent(
                            run_id=run_id,
                            span_id=f"span-{run_id}-3",
                            parent_span_id=f"span-{run_id}-2",
                            step_type=StepType.LLM,
                            name="gpt-5.4-mini",
                            input={
                                "prompt": (
                                    "Order ORD-ERR-100 is delayed. Check status and decide the "
                                    "next action.\n\nTool outputs:\nlookup_order_status: An "
                                    "error occurred while running the tool. Please try again. "
                                    "Error: tool backend unavailable for order 'ORD-ERR-100'"
                                )
                            },
                            output={
                                "output": "success",
                                "success": False,
                                "error": "tool backend unavailable for order 'ORD-ERR-100'",
                            },
                            token_usage=10,
                        ),
                    ],
                ),
            )

    from app.modules.runs.application.execution import RunExecutionService

    service = RunExecutionService(
        run_repository=run_repository,
        artifact_resolver=_FixedArtifactResolver(),
        runner=FailedToolPublishedRuntime(),
        telemetry_ingestor=_build_telemetry_ingestor(
            trace_repository=trace_repository,
            trajectory_repository=trajectory_repository,
        ),
    )

    payload = RunSpec(
        project="control-plane",
        dataset="fulfillment-eval-v1",
        agent_id="fulfillment_ops",
        model="gpt-5.4-mini",
        entrypoint="app.agent_plugins.fulfillment_ops:build_agent",
        agent_type=AdapterKind.OPENAI_AGENTS,
        input_summary="record tool failure trace",
        prompt="Order ORD-ERR-100 is delayed. Check status and decide the next action.",
    )

    service.execute_run(run_id, payload)

    run = run_repository.get(run_id)
    steps = trajectory_repository.list_for_run(run_id)

    assert run is not None
    assert run.status == RunStatus.FAILED
    assert run.runner_backend == "local-process"
    assert run.artifact_ref == "source://fulfillment_ops@fingerprint-test"
    assert run.error_code == "tool_execution"
    assert run.error_message == "tool backend unavailable for order 'ORD-ERR-100'"
    assert run.termination_reason == "tool backend unavailable for order 'ORD-ERR-100'"
    assert run.latency_ms == 15
    assert run.token_cost == 18
    assert run.tool_calls == 1
    assert [step.success for step in steps] == [True, False, False]


def test_run_execution_projector_handles_prompt_only_run():
    run_id = uuid4()
    context = RunExecutionContext.from_spec(
        run_id,
        RunSpec(
            project="control-plane",
            dataset=None,
            model="gpt-5.4-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
            input_summary="prompt only",
            prompt="Explain the plan.",
        ),
    )
    projector = RunExecutionProjector()

    record = projector.project_runtime_success(
        context,
        PublishedRunExecutionResult(
            runtime_result=RuntimeExecutionResult(
                output="ok",
                latency_ms=7,
                token_usage=11,
                provider="mock",
            )
        ),
    )

    assert record.events[0].input["prompt"] == "Explain the plan."
    assert record.events[0].input["model"] == "gpt-5.4-mini"
