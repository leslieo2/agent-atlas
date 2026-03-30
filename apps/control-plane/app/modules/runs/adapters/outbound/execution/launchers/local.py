from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_atlas_contracts.execution import RunnerBootstrapPaths, RunnerRunSpec

from app.modules.runs.application.results import PublishedRunExecutionResult
from app.modules.runs.application.runtime_translation import (
    empty_artifact_manifest,
    producer_for_runtime,
    terminal_result_from_runtime_result,
    trace_event_to_event_envelope,
)


@dataclass(frozen=True)
class LocalLaunchSession:
    payload: RunnerRunSpec
    work_dir: Path
    environment: dict[str, str]
    entrypoint_args: list[str]


class LocalLauncher:
    def __init__(self, workspace_root: Path | None = None) -> None:
        self.workspace_root = workspace_root

    def prepare(self, payload: RunnerRunSpec) -> LocalLaunchSession:
        work_dir = self._resolve_work_dir(payload)
        work_dir.mkdir(parents=True, exist_ok=True)

        bootstrap = self._materialize_bootstrap(payload.bootstrap, work_dir)
        materialized_payload = payload.model_copy(update={"bootstrap": bootstrap})
        self._ensure_directories(bootstrap)
        Path(bootstrap.run_spec_path).write_text(
            materialized_payload.model_dump_json(indent=2),
            encoding="utf-8",
        )

        return LocalLaunchSession(
            payload=materialized_payload,
            work_dir=work_dir,
            environment=bootstrap.as_environment(),
            entrypoint_args=bootstrap.as_entrypoint_args(),
        )

    def persist_result(
        self,
        session: LocalLaunchSession,
        result: PublishedRunExecutionResult,
    ) -> None:
        payload = session.payload
        event_envelopes = list(result.event_envelopes)
        if not event_envelopes and result.trace_events:
            producer = (
                result.terminal_result.producer
                if result.terminal_result is not None
                else producer_for_runtime(
                    runtime=result.runtime_result.provider,
                    framework=payload.framework,
                )
            )
            event_envelopes = [
                trace_event_to_event_envelope(
                    event,
                    experiment_id=payload.experiment_id,
                    attempt=payload.attempt,
                    attempt_id=payload.attempt_id,
                    producer=producer,
                    sequence=index,
                )
                for index, event in enumerate(result.trace_events, start=1)
            ]

        terminal_result = result.terminal_result
        if terminal_result is None:
            producer = (
                event_envelopes[0].producer
                if event_envelopes
                else producer_for_runtime(
                    runtime=result.runtime_result.provider,
                    framework=payload.framework,
                )
            )
            terminal_result = terminal_result_from_runtime_result(
                payload=payload,
                runtime_result=result.runtime_result,
                producer=producer,
                tool_calls=sum(
                    1 for event in event_envelopes if event.event_type.startswith("tool.")
                ),
            )

        artifact_manifest = result.artifact_manifest
        if artifact_manifest is None:
            artifact_manifest = empty_artifact_manifest(
                payload=payload,
                producer=terminal_result.producer,
            )

        self._write_ndjson(
            Path(payload.bootstrap.events_path),
            [event.model_dump(mode="json") for event in event_envelopes],
        )
        self._write_json(
            Path(payload.bootstrap.terminal_result_path),
            terminal_result.model_dump(mode="json"),
        )
        self._write_json(
            Path(payload.bootstrap.artifact_manifest_path),
            artifact_manifest.model_dump(mode="json"),
        )

    def _resolve_work_dir(self, payload: RunnerRunSpec) -> Path:
        configured_root = payload.executor_config.get("artifact_path")
        if isinstance(configured_root, str) and configured_root.strip():
            base_dir = Path(configured_root).expanduser()
        elif self.workspace_root is not None:
            base_dir = self.workspace_root
        else:
            base_dir = Path(tempfile.mkdtemp(prefix=f"agent-atlas-run-{str(payload.run_id)[:8]}-"))

        attempt_suffix = str(payload.attempt_id or payload.attempt)
        return base_dir / str(payload.run_id) / attempt_suffix

    @staticmethod
    def _materialize_bootstrap(
        bootstrap: RunnerBootstrapPaths,
        work_dir: Path,
    ) -> RunnerBootstrapPaths:
        return RunnerBootstrapPaths(
            run_spec_path=str(LocalLauncher._local_path(work_dir, bootstrap.run_spec_path)),
            events_path=str(LocalLauncher._local_path(work_dir, bootstrap.events_path)),
            terminal_result_path=str(
                LocalLauncher._local_path(work_dir, bootstrap.terminal_result_path)
            ),
            artifact_manifest_path=str(
                LocalLauncher._local_path(work_dir, bootstrap.artifact_manifest_path)
            ),
            artifact_dir=str(LocalLauncher._local_path(work_dir, bootstrap.artifact_dir)),
        )

    @staticmethod
    def _local_path(work_dir: Path, raw_path: str) -> Path:
        normalized = raw_path.lstrip("/") if Path(raw_path).is_absolute() else raw_path
        return work_dir / normalized

    @staticmethod
    def _ensure_directories(bootstrap: RunnerBootstrapPaths) -> None:
        Path(bootstrap.run_spec_path).parent.mkdir(parents=True, exist_ok=True)
        Path(bootstrap.events_path).parent.mkdir(parents=True, exist_ok=True)
        Path(bootstrap.terminal_result_path).parent.mkdir(parents=True, exist_ok=True)
        Path(bootstrap.artifact_manifest_path).parent.mkdir(parents=True, exist_ok=True)
        Path(bootstrap.artifact_dir).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _write_ndjson(path: Path, rows: list[dict[str, Any]]) -> None:
        content = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
        path.write_text(content + ("\n" if rows else ""), encoding="utf-8")
