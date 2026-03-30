from __future__ import annotations

import hashlib
import json
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from agent_atlas_contracts.execution import (
    ArtifactEntry,
    ArtifactManifest,
    EventEnvelope,
    RunnerBootstrapPaths,
    RunnerRunSpec,
    TerminalResult,
)


@dataclass(frozen=True)
class RunnerOutputFiles:
    run_spec_path: Path
    events_path: Path
    terminal_result_path: Path
    artifact_manifest_path: Path
    artifact_dir: Path


class RunnerOutputWriter:
    def __init__(self, bootstrap: RunnerBootstrapPaths) -> None:
        self.bootstrap = bootstrap
        self.files = RunnerOutputFiles(
            run_spec_path=Path(bootstrap.run_spec_path),
            events_path=Path(bootstrap.events_path),
            terminal_result_path=Path(bootstrap.terminal_result_path),
            artifact_manifest_path=Path(bootstrap.artifact_manifest_path),
            artifact_dir=Path(bootstrap.artifact_dir),
        )

    @classmethod
    def from_payload(cls, payload: RunnerRunSpec) -> RunnerOutputWriter:
        return cls(payload.bootstrap)

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> RunnerOutputWriter:
        source = dict(os.environ if environ is None else environ)
        return cls(
            RunnerBootstrapPaths(
                run_spec_path=source.get("ATLAS_RUNSPEC_PATH", "/workspace/input/run_spec.json"),
                events_path=source.get("ATLAS_EVENTS_PATH", "/workspace/output/events.ndjson"),
                terminal_result_path=source.get(
                    "ATLAS_TERMINAL_RESULT_PATH",
                    "/workspace/output/terminal_result.json",
                ),
                artifact_manifest_path=source.get(
                    "ATLAS_ARTIFACT_MANIFEST_PATH",
                    "/workspace/output/artifact_manifest.json",
                ),
                artifact_dir=source.get("ATLAS_ARTIFACT_DIR", "/workspace/output/artifacts"),
            )
        )

    def ensure_directories(self) -> None:
        self.files.run_spec_path.parent.mkdir(parents=True, exist_ok=True)
        self.files.events_path.parent.mkdir(parents=True, exist_ok=True)
        self.files.terminal_result_path.parent.mkdir(parents=True, exist_ok=True)
        self.files.artifact_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.files.artifact_dir.mkdir(parents=True, exist_ok=True)

    def load_run_spec(self) -> RunnerRunSpec:
        return RunnerRunSpec.model_validate_json(
            self.files.run_spec_path.read_text(encoding="utf-8")
        )

    def write_events(self, events: Sequence[EventEnvelope]) -> None:
        self.ensure_directories()
        rows = [event.model_dump(mode="json") for event in events]
        content = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
        self.files.events_path.write_text(content + ("\n" if rows else ""), encoding="utf-8")

    def write_terminal_result(self, result: TerminalResult) -> None:
        self.ensure_directories()
        self.files.terminal_result_path.write_text(
            json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def write_artifact_manifest(self, manifest: ArtifactManifest) -> None:
        self.ensure_directories()
        self.files.artifact_manifest_path.write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def write_artifact_text(
        self,
        relative_path: str,
        content: str,
        *,
        media_type: str | None = "text/plain",
        metadata: dict[str, object] | None = None,
    ) -> ArtifactEntry:
        artifact_path = self._artifact_path(relative_path)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(content, encoding="utf-8")
        return self.build_artifact_entry(
            artifact_path,
            relative_path=relative_path,
            media_type=media_type,
            metadata=metadata,
        )

    def write_artifact_bytes(
        self,
        relative_path: str,
        content: bytes,
        *,
        media_type: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> ArtifactEntry:
        artifact_path = self._artifact_path(relative_path)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_bytes(content)
        return self.build_artifact_entry(
            artifact_path,
            relative_path=relative_path,
            media_type=media_type,
            metadata=metadata,
        )

    def build_artifact_entry(
        self,
        path: Path,
        *,
        relative_path: str | None = None,
        media_type: str | None = None,
        metadata: dict[str, object] | None = None,
        uri: str | None = None,
    ) -> ArtifactEntry:
        resolved = path.resolve()
        artifact_root = self.files.artifact_dir.resolve()
        if not resolved.is_relative_to(artifact_root):
            raise ValueError("artifact path must stay within the configured artifact directory")

        manifest_path = relative_path or str(resolved.relative_to(artifact_root))
        detected_media_type = media_type or mimetypes.guess_type(resolved.name)[0]
        payload = resolved.read_bytes()
        return ArtifactEntry(
            path=manifest_path,
            kind="file",
            uri=uri,
            media_type=detected_media_type,
            size_bytes=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
            metadata=dict(metadata or {}),
        )

    def _artifact_path(self, relative_path: str) -> Path:
        candidate = self.files.artifact_dir / relative_path
        resolved = candidate.resolve()
        artifact_root = self.files.artifact_dir.resolve()
        if not resolved.is_relative_to(artifact_root):
            raise ValueError("artifact path must stay within the configured artifact directory")
        return resolved


__all__ = [
    "RunnerOutputFiles",
    "RunnerOutputWriter",
]
