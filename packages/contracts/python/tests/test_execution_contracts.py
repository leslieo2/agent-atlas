from __future__ import annotations

from uuid import UUID

from agent_atlas_contracts.execution import (
    RunnerBootstrapPaths,
    TerminalResult,
    encode_runner_callback,
    parse_runner_callback,
    runner_callback_envelope,
)


def test_runner_bootstrap_paths_expose_environment_and_entrypoint_args() -> None:
    paths = RunnerBootstrapPaths(
        run_spec_path="/tmp/input/run-spec.json",
        events_path="/tmp/output/events.ndjson",
        runtime_result_path="/tmp/output/runtime-result.json",
        terminal_result_path="/tmp/output/terminal-result.json",
        artifact_manifest_path="/tmp/output/artifact-manifest.json",
        artifact_dir="/tmp/output/artifacts",
    )

    assert paths.as_environment() == {
        "ATLAS_RUNSPEC_PATH": "/tmp/input/run-spec.json",
        "ATLAS_EVENTS_PATH": "/tmp/output/events.ndjson",
        "ATLAS_RUNTIME_RESULT_PATH": "/tmp/output/runtime-result.json",
        "ATLAS_TERMINAL_RESULT_PATH": "/tmp/output/terminal-result.json",
        "ATLAS_ARTIFACT_MANIFEST_PATH": "/tmp/output/artifact-manifest.json",
        "ATLAS_ARTIFACT_DIR": "/tmp/output/artifacts",
    }
    assert paths.as_entrypoint_args() == [
        "--run-spec",
        "/tmp/input/run-spec.json",
        "--events",
        "/tmp/output/events.ndjson",
        "--runtime-result",
        "/tmp/output/runtime-result.json",
        "--terminal-result",
        "/tmp/output/terminal-result.json",
        "--artifact-manifest",
        "/tmp/output/artifact-manifest.json",
        "--artifact-dir",
        "/tmp/output/artifacts",
    ]


def test_runner_callback_round_trip_preserves_terminal_result_payload() -> None:
    payload = TerminalResult(
        run_id=UUID("11111111-1111-1111-1111-111111111111"),
        status="succeeded",
        output="done",
    )

    envelope = runner_callback_envelope("terminal_result", payload)
    encoded = encode_runner_callback(envelope)

    parsed = parse_runner_callback(f"  {encoded}\n")

    assert parsed == envelope

