from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.bootstrap.container import get_container
from app.infrastructure.adapters.trace_projection import TraceIngestProjector
from app.modules.artifacts.domain.models import ArtifactExportRequest
from app.modules.datasets.domain.models import DatasetCreate
from app.modules.runs.application.results import PublishedRunExecutionResult
from app.modules.runs.domain.models import (
    RunCreateInput,
    RuntimeExecutionResult,
    TrajectoryStep,
)
from app.modules.shared.domain.enums import (
    ArtifactFormat,
    RunStatus,
    StepType,
)
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
    normalizer = TraceIngestProjector()
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
    container.agent_publication_commands.publish("basic")
    monkeypatch.setattr(
        container.model_runtime,
        "execute_published",
        lambda *_args, **_kwargs: PublishedRunExecutionResult(
            runtime_result=RuntimeExecutionResult(
                output="mocked unit output",
                latency_ms=1,
                token_usage=2,
                provider="mock",
                resolved_model="gpt-5.4-mini",
            )
        ),
    )
    payload = RunCreateInput(
        project="orchestrator",
        dataset="test-ds",
        agent_id="basic",
        input_summary="run test",
        prompt="run test prompt",
        tags=["ci"],
        project_metadata={},
    )
    run = container.run_commands.create_run(payload)

    assert worker_drain() >= 1

    trajectory = container.run_queries.get_trajectory(run.run_id)
    traces = container.run_queries.get_traces(run.run_id)

    assert len(trajectory) == 1
    assert len(traces) == 1
    assert [step.id for step in trajectory] == [span.span_id for span in traces]
    assert container.run_queries.get_run(run.run_id).status == RunStatus.SUCCEEDED
    assert container.run_queries.get_run(run.run_id).agent_id == "basic"


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
            model="gpt-5.4-mini",
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
