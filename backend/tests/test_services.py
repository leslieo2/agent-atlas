from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.db.state import state
from app.models.schemas import (
    ArtifactExportRequest,
    ArtifactFormat,
    DatasetCreate,
    EvalJobCreate,
    EvalStatus,
    ReplayRequest,
    RunCreateRequest,
    RunStatus,
    StepType,
    TrajectoryStep,
)
from app.services.adapter import adapter_manager
from app.services.datasets import dataset_service
from app.services.eval_service import eval_service
from app.services.exporter import exporter
from app.services.orchestrator import orchestrator
from app.services.replay import replay_service


@dataclass
class _TestStepType:
    value: str


def test_dataset_service_create_and_get():
    payload = DatasetCreate(
        name="test-ds",
        rows=[],
    )
    created = dataset_service.create(payload)
    assert created.name == "test-ds"
    assert dataset_service.get("test-ds") == created


def test_adapter_normalize_span_payload():
    run_id = uuid4()
    normalized = adapter_manager.normalize_span(
        run_id=run_id,
        payload=type(
            "Payload",
            (),
            {
                "span_id": "span-1",
                "parent_span_id": None,
                "step_type": _TestStepType("llm"),
                "input": {"prompt": "hi"},
                "output": {"output": "ok"},
                "tool_name": None,
                "latency_ms": 11,
                "token_usage": 22,
                "image_digest": "sha256:abc",
                "prompt_version": "v1",
                "received_at": type("TS", (), {"isoformat": lambda _: "2026-01-01T00:00:00Z"})(),
            },
        )(),
    )

    assert normalized["run_id"] == str(run_id)
    assert normalized["step_type"] == "llm"
    assert normalized["latency_ms"] == 11


def test_orchestrator_can_force_success(monkeypatch):
    monkeypatch.setattr(orchestrator.random, "random", lambda: 1.0)
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
    run = orchestrator.create_run(payload)

    deadline = time.time() + 2.0
    while time.time() < deadline:
        status = state.runs[run.run_id].status
        if status == RunStatus.SUCCEEDED:
            break
        time.sleep(0.05)
    else:
        raise AssertionError("run did not succeed in time")

    assert len(state.trajectory[run.run_id]) == 4
    assert len(state.trace_spans[run.run_id]) == 4
    assert state.runs[run.run_id].status == RunStatus.SUCCEEDED


def test_replay_service_creates_diffed_output():
    run_id = uuid4()
    step = TrajectoryStep(
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
    with state.lock:
        state.trajectory[run_id] = [step]

    request = ReplayRequest(
        run_id=run_id,
        step_id="seed-step",
        edited_prompt="updated prompt",
        model="gpt-4.1-mini",
    )

    result = replay_service.replay_step(request)
    assert result.run_id == run_id
    assert "Replay output for step seed-step" in result.replay_output
    assert "updated prompt" in result.updated_prompt
    assert "baseline" in result.diff


def test_exporter_jsonl_output(tmp_path):
    run_id = uuid4()
    with state.lock:
        state.trajectory[run_id] = [
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
        ]

    exporter.output_dir = Path(tmp_path)
    request = ArtifactExportRequest(run_ids=[run_id], format=ArtifactFormat.JSONL)
    artifact = exporter.export(request)

    path = Path(artifact.path)
    assert path.exists()
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert "seed-step" not in lines[0]
    assert "step-1" in lines[0]


def test_eval_job_runs_to_completion():
    run_id = uuid4()
    payload = EvalJobCreate(run_ids=[run_id], dataset="test-ds")
    job = eval_service.create_job(payload)

    deadline = time.time() + 2.0
    while time.time() < deadline:
        with state.lock:
            current_job = state.eval_jobs.get(job.job_id)
            if current_job and current_job.status == EvalStatus.DONE:
                break
        time.sleep(0.05)
    else:
        raise AssertionError("eval job did not complete in time")

    current_job = state.eval_jobs[job.job_id]
    assert current_job.status == EvalStatus.DONE
    assert len(current_job.results) == 1
