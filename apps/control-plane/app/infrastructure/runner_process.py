from __future__ import annotations

import argparse
import sys

from agent_atlas_contracts.execution import (
    RunnerBootstrapPaths,
    RunnerRunSpec,
    TerminalMetrics,
    TerminalResult,
)
from agent_atlas_contracts.runtime import empty_artifact_manifest, producer_for_runtime
from agent_atlas_runner_base.outputs import RunnerOutputWriter

from app.core.errors import AppError
from app.execution.adapters.launchers.local import persist_published_execution
from app.infrastructure.adapters.framework_registry import (
    PublishedAgentExecutionDispatcher,
    discover_framework_plugins,
)
from app.infrastructure.adapters.runtime import ModelRuntimeService


def _parse_args(argv: list[str] | None = None) -> RunnerBootstrapPaths:
    parser = argparse.ArgumentParser(prog="agent-atlas-runner-process")
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


def _failure_terminal_result(
    payload: RunnerRunSpec,
    exc: Exception,
) -> TerminalResult:
    if isinstance(exc, AppError):
        reason_code = exc.code
        reason_message = exc.message
        reason_context = dict(exc.context)
    else:
        reason_code = "runner_subprocess_failed"
        reason_message = str(exc).strip() or "runner subprocess failed"
        reason_context = {}

    return TerminalResult(
        run_id=payload.run_id,
        experiment_id=payload.experiment_id,
        attempt=payload.attempt,
        attempt_id=payload.attempt_id,
        status="failed",
        reason_code=reason_code,
        reason_message=reason_message,
        reason_context=reason_context,
        output=reason_message,
        producer=producer_for_runtime(
            runtime="local-subprocess",
            framework=payload.framework,
        ),
        metrics=TerminalMetrics(),
    )


def main(argv: list[str] | None = None) -> int:
    bootstrap = _parse_args(argv)
    writer = RunnerOutputWriter(bootstrap)
    payload = writer.load_run_spec()
    runtime = ModelRuntimeService(
        published_execution_dispatcher=PublishedAgentExecutionDispatcher(
            plugins=discover_framework_plugins(),
        )
    )

    try:
        result = runtime.execute_published(payload.run_id, payload)
        persist_published_execution(payload, result)
        return 0
    except Exception as exc:
        producer = producer_for_runtime(
            runtime="local-subprocess",
            framework=payload.framework,
        )
        writer.write_events([])
        writer.write_terminal_result(_failure_terminal_result(payload, exc))
        writer.write_artifact_manifest(empty_artifact_manifest(payload=payload, producer=producer))
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
