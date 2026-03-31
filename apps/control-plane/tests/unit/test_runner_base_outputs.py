from __future__ import annotations

import json
from uuid import uuid4

from agent_atlas_contracts.execution import (
    ArtifactManifest,
    EventEnvelope,
    ProducerInfo,
    RunnerBootstrapPaths,
    RunnerRunSpec,
    TerminalMetrics,
    TerminalResult,
)
from agent_atlas_contracts.runtime import RuntimeExecutionResult
from agent_atlas_runner_base.outputs import RunnerOutputWriter


def _runner_payload(tmp_path) -> RunnerRunSpec:
    return RunnerRunSpec(
        run_id=uuid4(),
        experiment_id=uuid4(),
        project="atlas",
        dataset="ops",
        agent_id="triage-bot",
        model="gpt-5.4-mini",
        entrypoint="atlas.agents:build",
        agent_type="openai_agents",
        prompt="Summarize the incident.",
        published_agent_snapshot={"manifest": {"agent_id": "triage-bot"}},
        bootstrap=RunnerBootstrapPaths(
            run_spec_path=str(tmp_path / "workspace/input/run_spec.json"),
            events_path=str(tmp_path / "workspace/output/events.ndjson"),
            runtime_result_path=str(tmp_path / "workspace/output/runtime_result.json"),
            terminal_result_path=str(tmp_path / "workspace/output/terminal_result.json"),
            artifact_manifest_path=str(tmp_path / "workspace/output/artifact_manifest.json"),
            artifact_dir=str(tmp_path / "workspace/output/artifacts"),
        ),
    )


def test_runner_output_writer_loads_from_environment_and_persists_contract_files(tmp_path):
    payload = _runner_payload(tmp_path)
    writer = RunnerOutputWriter(payload.bootstrap)
    writer.ensure_directories()
    writer.files.run_spec_path.write_text(payload.model_dump_json(indent=2), encoding="utf-8")

    from_env = RunnerOutputWriter.from_environment(payload.bootstrap.as_environment())
    loaded = from_env.load_run_spec()

    event = EventEnvelope(
        run_id=payload.run_id,
        experiment_id=payload.experiment_id,
        attempt=payload.attempt,
        attempt_id=payload.attempt_id,
        event_id="evt-1",
        sequence=1,
        event_type="llm.response",
        producer=ProducerInfo(runtime="mock", framework="mock"),
        payload={"output": {"success": True}},
    )
    terminal_result = TerminalResult(
        run_id=payload.run_id,
        experiment_id=payload.experiment_id,
        attempt=payload.attempt,
        attempt_id=payload.attempt_id,
        status="succeeded",
        producer=ProducerInfo(runtime="mock", framework="mock"),
        metrics=TerminalMetrics(latency_ms=12, token_usage=3, tool_calls=0),
    )
    runtime_result = RuntimeExecutionResult(
        output="done",
        latency_ms=12,
        token_usage=3,
        provider="mock",
        execution_backend="langgraph",
        container_image="ghcr.io/example/runner:123",
        resolved_model="gpt-5.4-mini-resolved",
    )
    artifact_entry = writer.write_artifact_text(
        "reports/summary.txt",
        "done",
        metadata={"kind": "summary"},
    )
    manifest = ArtifactManifest(
        run_id=payload.run_id,
        experiment_id=payload.experiment_id,
        attempt=payload.attempt,
        attempt_id=payload.attempt_id,
        producer=ProducerInfo(runtime="mock", framework="mock"),
        artifacts=[artifact_entry],
    )

    writer.write_events([event])
    writer.write_runtime_result(runtime_result)
    writer.write_terminal_result(terminal_result)
    writer.write_artifact_manifest(manifest)

    artifact_text = writer.files.artifact_dir.joinpath("reports/summary.txt").read_text(
        encoding="utf-8"
    )
    persisted_event = json.loads(writer.files.events_path.read_text(encoding="utf-8").strip())
    persisted_runtime = json.loads(writer.files.runtime_result_path.read_text(encoding="utf-8"))
    persisted_terminal = json.loads(writer.files.terminal_result_path.read_text(encoding="utf-8"))
    assert loaded.run_id == payload.run_id
    assert artifact_text == "done"
    assert persisted_event["event_id"] == "evt-1"
    assert persisted_runtime["execution_backend"] == "langgraph"
    assert persisted_terminal["status"] == "succeeded"
    persisted_manifest = json.loads(writer.files.artifact_manifest_path.read_text(encoding="utf-8"))
    assert persisted_manifest["artifacts"][0]["path"] == "reports/summary.txt"
    assert persisted_manifest["artifacts"][0]["metadata"]["kind"] == "summary"


def test_runner_output_writer_rejects_artifact_path_escape(tmp_path):
    payload = _runner_payload(tmp_path)
    writer = RunnerOutputWriter(payload.bootstrap)

    try:
        writer.write_artifact_text("../escape.txt", "blocked")
    except ValueError as exc:
        assert "artifact path" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected path escape to be rejected")
