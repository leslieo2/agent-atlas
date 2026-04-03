from __future__ import annotations

import argparse
import json
import os
import subprocess  # nosec B404 - explicit runner-side CLI invocation
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from agent_atlas_contracts.execution import (
    ArtifactManifest,
    EventEnvelope,
    RunnerBootstrapPaths,
    RunnerRunSpec,
    TerminalMetrics,
    TerminalResult,
)
from agent_atlas_contracts.runtime import RuntimeExecutionResult, producer_for_runtime

from agent_atlas_runner_base.constants import CLAUDE_CODE_CLI_RUNTIME
from agent_atlas_runner_base.outputs import RunnerOutputWriter
from agent_atlas_runner_base.materialization import (
    changed_files_manifest,
    materialize_project_bundle,
    project_materialization_from_executor_config,
    snapshot_tree,
)


def _string_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


class ClaudeCodeCliConfig:
    def __init__(
        self,
        *,
        command: Sequence[str],
        args: Sequence[str] | None = None,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        profile: str | None = None,
        system_prompt: str | None = None,
        version: str | None = None,
    ) -> None:
        self.command = list(command)
        self.args = list(args or [])
        self.cwd = cwd
        self.env = dict(env or {})
        self.profile = profile
        self.system_prompt = system_prompt
        self.version = version


def claude_code_cli_config_from_executor_config(
    executor_config: Mapping[str, Any],
) -> ClaudeCodeCliConfig | None:
    metadata = executor_config.get("metadata")
    if not isinstance(metadata, Mapping):
        return None
    raw_config = metadata.get("claude_code_cli")
    if not isinstance(raw_config, Mapping):
        return None

    raw_command = raw_config.get("command")
    if isinstance(raw_command, str):
        command = [raw_command.strip()] if raw_command.strip() else ["claude"]
    elif isinstance(raw_command, Sequence) and not isinstance(raw_command, str | bytes):
        command = [item.strip() for item in raw_command if isinstance(item, str) and item.strip()]
        if not command:
            command = ["claude"]
    else:
        command = ["claude"]

    raw_args = raw_config.get("args")
    args = (
        [item for item in raw_args if isinstance(item, str)]
        if isinstance(raw_args, Sequence) and not isinstance(raw_args, str | bytes)
        else []
    )

    raw_env = raw_config.get("env")
    env = (
        {
            key: value
            for key, value in raw_env.items()
            if isinstance(key, str) and isinstance(value, str)
        }
        if isinstance(raw_env, Mapping)
        else {}
    )

    return ClaudeCodeCliConfig(
        command=command,
        args=args,
        cwd=_string_value(raw_config.get("cwd")),
        env=env,
        profile=_string_value(raw_config.get("profile")),
        system_prompt=_string_value(raw_config.get("system_prompt")),
        version=_string_value(raw_config.get("version")),
    )


def claude_code_k8s_command(executor_config: Mapping[str, Any]) -> list[str] | None:
    if claude_code_cli_config_from_executor_config(executor_config) is None:
        return None
    return [sys.executable, "-m", "agent_atlas_runner_base.claude_code"]


def _parse_args(argv: list[str] | None = None) -> RunnerBootstrapPaths:
    parser = argparse.ArgumentParser(prog="agent-atlas-claude-code-runner")
    parser.add_argument("--run-spec", required=True)
    parser.add_argument("--events", required=True)
    parser.add_argument("--runtime-result", required=True)
    parser.add_argument("--terminal-result", required=True)
    parser.add_argument("--artifact-manifest", required=True)
    parser.add_argument("--artifact-dir", required=True)
    args = parser.parse_args(argv)
    return RunnerBootstrapPaths(
        run_spec_path=args.run_spec,
        events_path=args.events,
        runtime_result_path=args.runtime_result,
        terminal_result_path=args.terminal_result,
        artifact_manifest_path=args.artifact_manifest,
        artifact_dir=args.artifact_dir,
    )


def _extract_text(payload: object) -> str | None:
    if isinstance(payload, str):
        normalized = payload.strip()
        return normalized or None
    if isinstance(payload, Mapping):
        for key in ("result", "text", "message", "content", "summary", "output"):
            if key not in payload:
                continue
            candidate = _extract_text(payload.get(key))
            if candidate is not None:
                return candidate
    if isinstance(payload, Sequence) and not isinstance(payload, str | bytes):
        parts = [item for item in (_extract_text(item) for item in payload) if item]
        if parts:
            return "\n".join(parts)
    return None


def _event_type(raw_event_type: str) -> tuple[str, str]:
    normalized = raw_event_type.strip().lower()
    if "tool" in normalized:
        if "error" in normalized or "fail" in normalized:
            return ("tool.failed", "tool")
        return ("tool.succeeded", "tool")
    if normalized in {"error", "failed"}:
        return ("tool.failed", "tool")
    if normalized in {"result", "final", "message_stop"}:
        return ("llm.response", "llm")
    return ("llm.response", "llm")


def _build_event(
    *,
    payload: RunnerRunSpec,
    sequence: int,
    parent_event_id: str | None,
    raw_event: Mapping[str, Any],
    producer_version: str | None,
) -> EventEnvelope:
    raw_event_type = str(raw_event.get("type") or "message")
    event_type, step_type = _event_type(raw_event_type)
    text = _extract_text(raw_event)
    return EventEnvelope(
        run_id=payload.run_id,
        experiment_id=payload.experiment_id,
        attempt=payload.attempt,
        attempt_id=payload.attempt_id,
        event_id=f"claude-code-{sequence}",
        parent_event_id=parent_event_id,
        sequence=sequence,
        event_type=event_type,
        producer=producer_for_runtime(
            runtime=CLAUDE_CODE_CLI_RUNTIME,
            framework=payload.framework,
            version=producer_version,
        ),
        payload={
            "step_type": step_type,
            "name": raw_event_type,
            "input": {"prompt": payload.prompt},
            "output": {
                "output": text or json.dumps(raw_event, ensure_ascii=False),
                "success": event_type != "tool.failed",
                "event": dict(raw_event),
            },
            "latency_ms": 0,
            "token_usage": 0,
        },
    )


def _command_for_payload(payload: RunnerRunSpec) -> tuple[list[str], ClaudeCodeCliConfig]:
    config = claude_code_cli_config_from_executor_config(payload.executor_config)
    if config is None:
        raise RuntimeError("executor_config.metadata.claude_code_cli is required")

    command = [
        *config.command,
        *config.args,
        "--print",
        "--verbose",
        "--output-format",
        "stream-json",
    ]
    if config.profile is not None:
        command.extend(["--profile", config.profile])
    if config.system_prompt is not None:
        command.extend(["--system-prompt", config.system_prompt])
    command.append(payload.prompt)
    return command, config


def _neutral_execution_backend(payload: RunnerRunSpec) -> str | None:
    if payload.runner_backend == "k8s-container":
        return "kubernetes-job"
    backend = payload.executor_config.get("backend")
    return backend if isinstance(backend, str) and backend.strip() else payload.runner_backend


def _terminal_artifacts(
    *,
    writer: RunnerOutputWriter,
    stdout: str,
    stderr: str,
    payload: RunnerRunSpec,
    producer_version: str | None,
) -> ArtifactManifest:
    artifacts = []
    transcript_entry = writer.write_artifact_text(
        "transcripts/claude-stream.jsonl",
        stdout,
        metadata={"runner_family": CLAUDE_CODE_CLI_RUNTIME},
    )
    artifacts.append(transcript_entry)
    if stderr.strip():
        artifacts.append(
            writer.write_artifact_text(
                "logs/claude-stderr.txt",
                stderr,
                metadata={"runner_family": CLAUDE_CODE_CLI_RUNTIME},
            )
        )
    return ArtifactManifest(
        run_id=payload.run_id,
        experiment_id=payload.experiment_id,
        attempt=payload.attempt,
        attempt_id=payload.attempt_id,
        producer=producer_for_runtime(
            runtime=CLAUDE_CODE_CLI_RUNTIME,
            framework=payload.framework,
            version=producer_version,
        ),
        artifacts=artifacts,
    )


def _write_failure_outputs(
    *,
    writer: RunnerOutputWriter,
    payload: RunnerRunSpec,
    producer_version: str | None,
    reason_code: str,
    reason_message: str,
    execution_backend: str | None,
) -> int:
    latency_ms = 0
    artifacts = [
        writer.write_artifact_text(
            "logs/materialization-error.txt",
            reason_message,
            metadata={"runner_family": CLAUDE_CODE_CLI_RUNTIME, "kind": "materialization_error"},
        )
    ]
    writer.write_artifact_manifest(
        ArtifactManifest(
            run_id=payload.run_id,
            experiment_id=payload.experiment_id,
            attempt=payload.attempt,
            attempt_id=payload.attempt_id,
            producer=producer_for_runtime(
                runtime=CLAUDE_CODE_CLI_RUNTIME,
                framework=payload.framework,
                version=producer_version,
            ),
            artifacts=artifacts,
        )
    )
    writer.write_runtime_result(
        RuntimeExecutionResult(
            output=reason_message,
            latency_ms=latency_ms,
            token_usage=0,
            provider=CLAUDE_CODE_CLI_RUNTIME,
            execution_backend=execution_backend,
            resolved_model=payload.model,
        )
    )
    writer.write_terminal_result(
        TerminalResult(
            run_id=payload.run_id,
            experiment_id=payload.experiment_id,
            attempt=payload.attempt,
            attempt_id=payload.attempt_id,
            status="failed",
            reason_code=reason_code,
            reason_message=reason_message,
            exit_code=1,
            output=reason_message,
            producer=producer_for_runtime(
                runtime=CLAUDE_CODE_CLI_RUNTIME,
                framework=payload.framework,
                version=producer_version,
            ),
            metrics=TerminalMetrics(
                latency_ms=latency_ms,
                token_usage=0,
                tool_calls=0,
            ),
        )
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    bootstrap = _parse_args(argv)
    writer = RunnerOutputWriter(bootstrap)
    payload = writer.load_run_spec()
    command, config = _command_for_payload(payload)
    execution_backend = _neutral_execution_backend(payload)
    try:
        materialization = project_materialization_from_executor_config(payload.executor_config)
    except Exception as exc:
        return _write_failure_outputs(
            writer=writer,
            payload=payload,
            producer_version=config.version,
            reason_code="workspace_materialization_failed",
            reason_message=str(exc),
            execution_backend=execution_backend,
        )
    workspace_root: Path | None = None
    workspace_before: dict[str, str] = {}
    if materialization is not None:
        try:
            workspace_root = materialize_project_bundle(materialization)
        except Exception as exc:
            return _write_failure_outputs(
                writer=writer,
                payload=payload,
                producer_version=config.version,
                reason_code="workspace_materialization_failed",
                reason_message=str(exc),
                execution_backend=execution_backend,
            )
        workspace_before = snapshot_tree(workspace_root)

    started_at = time.time()
    completed = subprocess.run(  # nosec B603
        command,
        cwd=(
            str(workspace_root)
            if workspace_root is not None
            else config.cwd or os.getcwd()
        ),
        env={**os.environ, **config.env},
        capture_output=True,
        text=True,
        check=False,
    )

    raw_events: list[dict[str, Any]] = []
    final_output = ""
    for raw_line in completed.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            decoded = json.loads(line)
        except json.JSONDecodeError:
            decoded = {"type": "message", "text": line}
        if isinstance(decoded, Mapping):
            raw_event = dict(decoded)
        else:
            raw_event = {"type": "message", "text": str(decoded)}
        raw_events.append(raw_event)
        extracted = _extract_text(raw_event)
        if extracted:
            final_output = extracted

    events: list[EventEnvelope] = []
    previous_event_id: str | None = None
    for index, event in enumerate(raw_events, start=1):
        envelope = _build_event(
            payload=payload,
            sequence=index,
            parent_event_id=previous_event_id,
            raw_event=event,
            producer_version=config.version,
        )
        events.append(envelope)
        previous_event_id = envelope.event_id
    writer.write_events(events)

    artifact_manifest = _terminal_artifacts(
        writer=writer,
        stdout=completed.stdout,
        stderr=completed.stderr,
        payload=payload,
        producer_version=config.version,
    )
    if workspace_root is not None:
        workspace_after = snapshot_tree(workspace_root)
        changed_manifest = changed_files_manifest(before=workspace_before, after=workspace_after)
        artifact_manifest.artifacts.append(
            writer.write_artifact_text(
                "workspace/changed-files.json",
                json.dumps(changed_manifest, indent=2, ensure_ascii=False),
                media_type="application/json",
                metadata={"runner_family": CLAUDE_CODE_CLI_RUNTIME, "kind": "changed_files_manifest"},
            )
        )
    writer.write_artifact_manifest(artifact_manifest)

    latency_ms = max(int((time.time() - started_at) * 1000), 0)
    runtime_result = RuntimeExecutionResult(
        output=final_output or completed.stdout.strip() or completed.stderr.strip(),
        latency_ms=latency_ms,
        token_usage=0,
        provider=CLAUDE_CODE_CLI_RUNTIME,
        execution_backend=execution_backend,
        resolved_model=payload.model,
    )
    writer.write_runtime_result(runtime_result)

    terminal_status = "succeeded" if completed.returncode == 0 else "failed"
    tool_calls = sum(1 for event in events if event.payload.get("step_type") == "tool")
    writer.write_terminal_result(
        TerminalResult(
            run_id=payload.run_id,
            experiment_id=payload.experiment_id,
            attempt=payload.attempt,
            attempt_id=payload.attempt_id,
            status=terminal_status,
            reason_code=None if completed.returncode == 0 else "claude_code_cli_failed",
            reason_message=None
            if completed.returncode == 0
            else completed.stderr.strip() or "claude code cli failed",
            exit_code=completed.returncode,
            output=runtime_result.output,
            producer=producer_for_runtime(
                runtime=CLAUDE_CODE_CLI_RUNTIME,
                framework=payload.framework,
                version=config.version,
            ),
            metrics=TerminalMetrics(
                latency_ms=latency_ms,
                token_usage=0,
                tool_calls=tool_calls,
            ),
        )
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
