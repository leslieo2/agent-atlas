from __future__ import annotations

import random
from uuid import uuid4

import pytest
from app.infrastructure.repositories import StateEvalJobRepository
from app.modules.evals.application.execution import (
    EvalJobRecorder,
    EvalJobRunner,
    EvalSampleEvaluator,
)
from app.modules.evals.domain.models import EvalJob, EvalJobCreate
from app.modules.replays.application.execution import (
    ReplayBaselineResolver,
    ReplayExecutor,
    ReplayResultFactory,
)
from app.modules.replays.domain.models import ReplayRequest
from app.modules.runs.domain.models import RunRecord, RuntimeExecutionResult, TrajectoryStep
from app.modules.shared.domain.enums import AdapterKind, EvalStatus, RunStatus, StepType


def test_replay_baseline_resolver_rejects_memory_steps():
    resolver = ReplayBaselineResolver()
    run_id = uuid4()

    with pytest.raises(ValueError, match="does not support replay"):
        resolver.resolve(
            [
                TrajectoryStep(
                    id="memory-step",
                    run_id=run_id,
                    step_type=StepType.MEMORY,
                    prompt="persist",
                    output="done",
                    model="recorder",
                )
            ],
            "memory-step",
        )


def test_replay_result_factory_builds_diffed_result():
    run_id = uuid4()
    baseline = TrajectoryStep(
        id="step-1",
        run_id=run_id,
        step_type=StepType.LLM,
        prompt="Explain the plan.",
        output="baseline-output",
        model="gpt-4.1-mini",
        temperature=0.2,
    )
    request = ReplayRequest(
        run_id=run_id,
        step_id="step-1",
        edited_prompt="Explain the plan with more detail.",
        model="gpt-4.1",
    )
    replay_output = RuntimeExecutionResult(
        output="live replay output",
        latency_ms=12,
        token_usage=8,
        provider="stub",
    )

    result = ReplayResultFactory().build(request, baseline, replay_output)

    assert result.updated_prompt == "Explain the plan with more detail."
    assert result.model == "gpt-4.1"
    assert result.baseline_output == "baseline-output"
    assert result.diff


def test_replay_executor_runs_isolated_step_via_runner():
    run_id = uuid4()
    baseline = TrajectoryStep(
        id="step-1",
        run_id=run_id,
        step_type=StepType.LLM,
        prompt="Explain the plan.",
        output="baseline-output",
        model="gpt-4.1-mini",
        temperature=0.2,
    )
    run = RunRecord(
        run_id=run_id,
        input_summary="seed run",
        status=RunStatus.SUCCEEDED,
        project="workbench",
        dataset="crm-v2",
        model="gpt-4.1-mini",
        agent_type=AdapterKind.OPENAI_AGENTS,
        tags=["replay"],
    )
    request = ReplayRequest(
        run_id=run_id,
        step_id="step-1",
        edited_prompt="Explain the plan with more detail.",
        model="gpt-4.1",
        tool_overrides={"carrier": "UPS"},
        rationale="debug failed branch",
    )

    class StubRunner:
        def __init__(self) -> None:
            self.calls: list[tuple[AdapterKind, str, str]] = []

        def execute(
            self,
            agent_type: AdapterKind,
            model: str,
            prompt: str,
        ) -> RuntimeExecutionResult:
            self.calls.append((agent_type, model, prompt))
            return RuntimeExecutionResult(
                output="live replay output",
                latency_ms=17,
                token_usage=42,
                provider="stub",
            )

    class StubRegistry:
        def __init__(self, runner: StubRunner) -> None:
            self.runner = runner

        def get_runner(self, agent_type: AdapterKind) -> StubRunner:
            return self.runner

    runner = StubRunner()
    executor = ReplayExecutor(runner_registry=StubRegistry(runner))

    result = executor.execute(request, baseline, run)

    assert result.output == "live replay output"
    assert runner.calls == [
        (
            AdapterKind.OPENAI_AGENTS,
            "gpt-4.1",
            (
                "Explain the plan with more detail.\n\n"
                "Replay rationale:\n"
                "debug failed branch\n\n"
                "Tool overrides:\n"
                '{"carrier": "UPS"}'
            ),
        )
    ]


def test_eval_job_runner_marks_failure_when_evaluator_raises():
    repository = StateEvalJobRepository()
    job = EvalJob(run_ids=[uuid4()], dataset="crm-v2")
    repository.save(job)

    class ExplodingEvaluator(EvalSampleEvaluator):
        def evaluate(self, *, run_id, dataset, sample_index, rng):  # type: ignore[override]
            raise RuntimeError("boom")

    runner = EvalJobRunner(
        evaluator=ExplodingEvaluator(),
        recorder=EvalJobRecorder(eval_job_repository=repository),
    )

    runner.run(job.job_id, EvalJobCreate(run_ids=job.run_ids, dataset=job.dataset))

    failed = repository.get(job.job_id)
    assert failed is not None
    assert failed.status == EvalStatus.FAILED
    assert failed.failure_reason == "boom"


def test_eval_sample_evaluator_builds_deterministic_result():
    evaluator = EvalSampleEvaluator()
    run_id = uuid4()
    rng = random.Random(7)

    result = evaluator.evaluate(
        run_id=run_id,
        dataset="crm-v2",
        sample_index=0,
        rng=rng,
    )

    assert result.sample_id.startswith("sample-1-")
    assert result.run_id == run_id
    assert result.input == "dataset sample #1 from crm-v2"
    assert result.status in {"pass", "fail"}
