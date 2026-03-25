from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.bootstrap.container import get_container
from app.infrastructure.adapters.traces import DefaultTraceProjector
from app.modules.artifacts.domain.models import ArtifactExportRequest
from app.modules.datasets.domain.models import DatasetCreate
from app.modules.evals.domain.models import EvalJobCreate
from app.modules.replays.domain.models import ReplayRequest
from app.modules.runs.domain.models import RunSpec as RunCreateRequest
from app.modules.runs.domain.models import TrajectoryStep
from app.modules.shared.domain.enums import ArtifactFormat, EvalStatus, RunStatus, StepType
from app.modules.traces.domain.models import TraceIngestEvent, TraceSpan


def test_dataset_service_create_and_get():
    container = get_container()
    payload = DatasetCreate(
        name="test-ds",
        rows=[],
    )
    created = container.dataset_commands.create(payload)
    assert created.name == "test-ds"
    assert container.dataset_queries.get("test-ds") == created


def test_adapter_normalize_span_payload():
    normalizer = DefaultTraceProjector()
    run_id = uuid4()
    event = TraceIngestEvent(
        run_id=run_id,
        span_id="span-1",
        parent_span_id=None,
        step_type=StepType.LLM,
        name="normalize",
        input={"prompt": "hi"},
        output={"output": "ok"},
        tool_name=None,
        latency_ms=11,
        token_usage=22,
        image_digest="sha256:abc",
        prompt_version="v1",
    )
    span = TraceSpan(
        run_id=run_id,
        span_id="span-1",
        parent_span_id=None,
        step_type=StepType.LLM,
        input={"prompt": "hi"},
        output={"output": "ok"},
        tool_name=None,
        latency_ms=11,
        token_usage=22,
        image_digest="sha256:abc",
        prompt_version="v1",
    )
    normalized = normalizer.normalize(event=event, span=span)

    assert normalized["run_id"] == str(run_id)
    assert normalized["step_type"] == "llm"
    assert normalized["latency_ms"] == 11


def test_run_commands_can_force_success(monkeypatch, worker_drain):
    container = get_container()
    monkeypatch.setattr(
        "app.infrastructure.adapters.runner.execute_with_fallback",
        lambda *_args, **_kwargs: {
            "output": "mocked unit output",
            "latency_ms": 1,
            "token_usage": 2,
            "provider": "mock",
        },
    )
    payload = RunCreateRequest(
        project="orchestrator",
        dataset="test-ds",
        model="gpt-4.1-mini",
        agent_type="openai-agents-sdk",
        input_summary="run test",
        prompt="run test prompt",
        tags=["ci"],
        tool_config={"primary_tool": "mock"},
        project_metadata={},
    )
    run = container.run_commands.create_run(payload)

    assert worker_drain() >= 1

    trajectory = container.run_queries.get_trajectory(run.run_id)
    traces = container.run_queries.get_traces(run.run_id)

    assert len(trajectory) == 4
    assert len(traces) == 4
    assert [step.id for step in trajectory] == [span.span_id for span in traces]
    assert container.run_queries.get_run(run.run_id).status == RunStatus.SUCCEEDED


def test_replay_commands_create_diffed_output():
    container = get_container()
    run_id = uuid4()
    container.trajectory_repository.append(
        TrajectoryStep(
            id="seed-step",
            run_id=run_id,
            step_type=StepType.TOOL,
            prompt="baseline prompt",
            output="baseline-output",
            model="planner-v1",
            temperature=0.1,
            latency_ms=123,
            token_usage=10,
            success=True,
            tool_name="search",
        )
    )

    request = ReplayRequest(
        run_id=run_id,
        step_id="seed-step",
        edited_prompt="updated prompt",
        model="gpt-4.1-mini",
    )

    result = container.replay_commands.replay_step(request)
    assert result.run_id == run_id
    assert "Replay output for step seed-step" in result.replay_output
    assert "updated prompt" in result.updated_prompt
    assert "baseline" in result.diff


def test_artifact_commands_jsonl_output(tmp_path):
    container = get_container()
    run_id = uuid4()
    container.trajectory_repository.append(
        TrajectoryStep(
            id="step-1",
            run_id=run_id,
            step_type=StepType.LLM,
            prompt="hello",
            output="world",
            model="gpt-4.1-mini",
            temperature=0.0,
            latency_ms=10,
            token_usage=20,
            success=True,
        )
    )

    container.artifact_exporter.output_dir = Path(tmp_path)
    request = ArtifactExportRequest(run_ids=[run_id], format=ArtifactFormat.JSONL)
    artifact = container.artifact_commands.export(request)

    path = Path(artifact.path)
    assert path.exists()
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert "seed-step" not in lines[0]
    assert "step-1" in lines[0]


def test_eval_job_commands_run_to_completion(worker_drain):
    container = get_container()
    run_id = uuid4()
    payload = EvalJobCreate(run_ids=[run_id], dataset="test-ds")
    job = container.eval_job_commands.create_job(payload)

    assert worker_drain() >= 1

    current_job = container.eval_job_queries.get_job(job.job_id)
    assert current_job.status == EvalStatus.DONE
    assert len(current_job.results) == 1
