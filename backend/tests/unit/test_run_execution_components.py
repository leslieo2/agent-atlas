from __future__ import annotations

from uuid import uuid4

from app.infrastructure.adapters.traces import DefaultTraceProjector
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
from app.modules.runs.application.results import PublishedRunExecutionResult
from app.modules.runs.domain.models import (
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


def test_run_execution_projector_builds_success_trace_event():
    run_id = uuid4()
    context = RunExecutionContext.from_spec(
        run_id,
        RunSpec(
            project="control-plane",
            dataset="crm-v2",
            model="gpt-4.1-mini",
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
            model="gpt-4.1-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
            status=RunStatus.RUNNING,
        )
    )

    trace_ingestor = TraceCommands(
        workflow=TraceIngestionWorkflow(
            trace_projector=DefaultTraceProjector(),
            trace_recorder=TraceRecorder(
                trace_repository=trace_repository,
                trajectory_repository=trajectory_repository,
            ),
        )
    )

    context = RunExecutionContext.from_spec(
        run_id,
        RunSpec(
            project="control-plane",
            dataset="crm-v2",
            model="gpt-4.1-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
            input_summary="record metrics",
            prompt="Record this execution.",
        ),
    )
    projector = RunExecutionProjector()
    recorder = ExecutionRecorder(
        run_repository=run_repository,
        trace_ingestor=trace_ingestor,
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
            model="gpt-4.1-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
            status=RunStatus.RUNNING,
        )
    )

    trace_ingestor = TraceCommands(
        workflow=TraceIngestionWorkflow(
            trace_projector=DefaultTraceProjector(),
            trace_recorder=TraceRecorder(
                trace_repository=trace_repository,
                trajectory_repository=trajectory_repository,
            ),
        )
    )

    context = RunExecutionContext.from_spec(
        run_id,
        RunSpec(
            project="control-plane",
            dataset="crm-v2",
            model="gpt-4.1-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
            input_summary="record tool metrics",
            prompt="Use the tool before answering.",
        ),
    )
    projector = RunExecutionProjector()
    recorder = ExecutionRecorder(
        run_repository=run_repository,
        trace_ingestor=trace_ingestor,
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
                        name="gpt-4.1-mini",
                        input={"prompt": "Use the tool before answering.", "model": "gpt-4.1-mini"},
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
                        name="gpt-4.1-mini",
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


def test_run_execution_projector_handles_prompt_only_run():
    run_id = uuid4()
    context = RunExecutionContext.from_spec(
        run_id,
        RunSpec(
            project="control-plane",
            dataset=None,
            model="gpt-4.1-mini",
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
    assert record.events[0].input["model"] == "gpt-4.1-mini"
