from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from agent_atlas_contracts.execution import RunnerBootstrapPaths, RunnerRunSpec


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
