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
from app.modules.runs.domain.models import RunRecord, RunSpec, RuntimeExecutionResult
from app.modules.shared.domain.enums import AdapterKind, RunStatus
from app.modules.traces.application.use_cases import (
    TraceCommands,
    TraceIngestionWorkflow,
    TraceRecorder,
)


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
        RuntimeExecutionResult(
            output="Projected success output",
            latency_ms=17,
            token_usage=31,
            provider="mock",
            execution_backend="local",
            container_image="python:3.12-slim",
        ),
    )

    assert record.event.span_id == f"span-{run_id}-3"
    assert record.event.parent_span_id == f"span-{run_id}-2"
    assert record.event.output["output"] == "Projected success output"
    assert record.event.output["provider"] == "mock"
    assert record.event.image_digest == "python:3.12-slim"
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

    recorder.record(run_id, projector.project_planner(context))
    recorder.record(run_id, projector.project_runtime_preamble(context))
    recorder.record(
        run_id,
        projector.project_runtime_success(
            context,
            RuntimeExecutionResult(
                output="ok",
                latency_ms=9,
                token_usage=13,
                provider="mock",
            ),
        ),
    )

    run = run_repository.get(run_id)
    steps = trajectory_repository.list_for_run(run_id)
    spans = trace_repository.list_for_run(run_id)

    assert run is not None
    assert run.latency_ms == 12
    assert run.token_cost == 13
    assert run.tool_calls == 1
    expected_span_ids = [
        f"span-{run_id}-1",
        f"span-{run_id}-2",
        f"span-{run_id}-3",
    ]
    assert [step.id for step in steps] == expected_span_ids
    assert [step.parent_step_id for step in steps] == [None, f"span-{run_id}-1", f"span-{run_id}-2"]
    assert [span.span_id for span in spans] == expected_span_ids
