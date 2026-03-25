from __future__ import annotations

from uuid import uuid4

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


def test_run_execution_projector_builds_success_step_and_trace():
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

    assert record.step.id == f"{run_id}-step-3"
    assert record.step.output == "Projected success output"
    assert record.span.parent_span_id == f"span-{run_id}-1"
    assert record.span.output["provider"] == "mock"
    assert record.span.image_digest == "python:3.12-slim"
    assert record.metrics.token_cost == 31


def test_execution_recorder_persists_step_span_and_metrics():
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
        trajectory_repository=trajectory_repository,
        trace_repository=trace_repository,
    )

    recorder.record(run_id, projector.project_planner(context))
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
    assert run.latency_ms == 10
    assert run.token_cost == 13
    assert run.tool_calls == 0
    assert [step.id for step in steps] == [f"{run_id}-step-1", f"{run_id}-step-3"]
    assert [span.span_id for span in spans] == [f"span-{run_id}-1", f"span-{run_id}-3"]
