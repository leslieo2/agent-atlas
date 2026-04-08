from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import pytest
from agent_atlas_contracts.execution import (
    RUNNER_CALLBACK_MODE_ENV,
    RUNNER_CALLBACK_MODE_STDOUT_JSONL,
    RUNNER_CALLBACK_PREFIX,
    ArtifactManifest,
    EventEnvelope,
    ProducerInfo,
    RunnerBootstrapPaths,
    RunnerRunSpec,
    TerminalResult,
)
from agent_atlas_contracts.runtime import RuntimeExecutionResult
from agent_atlas_runner_base.outputs import RunnerOutputWriter


def test_runner_output_writer_loads_run_spec_and_writes_outputs(tmp_path: Path) -> None:
    writer = RunnerOutputWriter(_bootstrap_paths(tmp_path))
    payload = RunnerRunSpec(
        run_id=UUID("11111111-1111-1111-1111-111111111111"),
        runner_backend="local-process",
        project="atlas-validation",
        dataset="controlled-validation",
        agent_id="basic",
        model="gpt-5.4-mini",
        agent_type="openai-agents",
        prompt="Validate this asset",
        published_agent_snapshot={
            "manifest": {
                "agent_id": "basic",
                "name": "Basic",
                "description": "Fixture",
                "framework": "openai-agents-sdk",
                "default_model": "gpt-5.4-mini",
            },
            "entrypoint": "snapshots/basic:run",
        },
        bootstrap=_bootstrap_paths(tmp_path),
    )
    writer.ensure_directories()
    writer.files.run_spec_path.write_text(payload.model_dump_json(), encoding="utf-8")

    loaded = writer.load_run_spec()
    event = EventEnvelope(
        run_id=payload.run_id,
        event_id="event-1",
        event_type="llm.response",
        producer=ProducerInfo(runtime="unit-test"),
        payload={
            "step_type": "llm",
            "name": "gpt-5.4-mini",
            "input": {"prompt": payload.prompt},
            "output": {"output": "done", "success": True},
        },
    )
    runtime_result = RuntimeExecutionResult(
        output="done",
        latency_ms=42,
        token_usage=9,
        provider="openai-agents-sdk",
    )
    terminal_result = TerminalResult(
        run_id=payload.run_id,
        status="succeeded",
        output="done",
    )
    artifact_entry = writer.write_artifact_text(
        "logs/output.txt",
        "hello world",
        metadata={"kind": "log"},
    )
    manifest = ArtifactManifest(
        run_id=payload.run_id,
        producer=ProducerInfo(runtime="unit-test"),
        artifacts=[artifact_entry],
    )

    writer.write_events([event])
    writer.write_runtime_result(runtime_result)
    writer.write_terminal_result(terminal_result)
    writer.write_artifact_manifest(manifest)

    assert loaded == payload
    assert writer.files.events_path.exists()
    assert writer.files.runtime_result_path.exists()
    assert writer.files.terminal_result_path.exists()
    assert writer.files.artifact_manifest_path.exists()
    assert writer.files.artifact_dir.joinpath("logs/output.txt").read_text(encoding="utf-8") == "hello world"

    rows = writer.files.events_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(rows) == 1
    assert json.loads(rows[0])["event_id"] == "event-1"
    assert json.loads(writer.files.runtime_result_path.read_text(encoding="utf-8"))["provider"] == "openai-agents-sdk"
    assert json.loads(writer.files.artifact_manifest_path.read_text(encoding="utf-8"))["artifacts"][0]["path"] == "logs/output.txt"


def test_runner_output_writer_emits_stdout_callbacks_when_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(RUNNER_CALLBACK_MODE_ENV, RUNNER_CALLBACK_MODE_STDOUT_JSONL)
    writer = RunnerOutputWriter(_bootstrap_paths(tmp_path))

    writer.write_runtime_result(
        RuntimeExecutionResult(
            output="done",
            latency_ms=12,
            token_usage=3,
            provider="langchain",
        )
    )

    captured = capsys.readouterr()
    assert RUNNER_CALLBACK_PREFIX in captured.out
    assert "\"kind\":\"runtime_result\"" in captured.out


def test_runner_output_writer_rejects_artifact_path_traversal(tmp_path: Path) -> None:
    writer = RunnerOutputWriter(_bootstrap_paths(tmp_path))

    with pytest.raises(ValueError, match="artifact path must stay within the configured artifact directory"):
        writer.write_artifact_text("../escape.txt", "nope")


def _bootstrap_paths(tmp_path: Path) -> RunnerBootstrapPaths:
    return RunnerBootstrapPaths(
        run_spec_path=str(tmp_path / "input" / "run_spec.json"),
        events_path=str(tmp_path / "output" / "events.ndjson"),
        runtime_result_path=str(tmp_path / "output" / "runtime_result.json"),
        terminal_result_path=str(tmp_path / "output" / "terminal_result.json"),
        artifact_manifest_path=str(tmp_path / "output" / "artifact_manifest.json"),
        artifact_dir=str(tmp_path / "output" / "artifacts"),
    )

