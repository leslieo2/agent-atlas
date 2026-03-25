from __future__ import annotations

import json
import os
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.modules.artifacts.application.ports import (
    ArtifactRepository,
    RunLookupSource,
    TrajectoryExportSource,
)
from app.modules.artifacts.domain.models import ArtifactExportRequest, ArtifactMetadata
from app.modules.runs.domain.models import RunRecord, TrajectoryStep
from app.modules.shared.domain.enums import ArtifactFormat


class ArtifactExporterAdapter:
    def __init__(
        self,
        trajectory_repository: TrajectoryExportSource,
        artifact_repository: ArtifactRepository,
        run_repository: RunLookupSource,
    ) -> None:
        self.trajectory_repository = trajectory_repository
        self.artifact_repository = artifact_repository
        self.run_repository = run_repository
        self.output_dir = Path(__file__).resolve().parents[3] / "data" / "artifacts"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, payload: ArtifactExportRequest) -> ArtifactMetadata:
        artifact_id = uuid4()
        extension = payload.format.value
        path = self.output_dir / f"{artifact_id}.{extension}"
        if payload.format == ArtifactFormat.JSONL:
            self._export_jsonl(payload, path)
        else:
            self._export_parquet_fallback(payload, path)
        metadata = ArtifactMetadata(
            artifact_id=artifact_id,
            format=payload.format,
            run_ids=payload.run_ids,
            path=str(path),
            size_bytes=path.stat().st_size,
        )
        self.artifact_repository.save(metadata)
        return metadata

    def _export_jsonl(self, payload: ArtifactExportRequest, path: Path) -> None:
        records = []
        for run_id in payload.run_ids:
            records.extend(self._build_records_for_run(payload, run_id))
        with path.open("w", encoding="utf-8") as handle:
            for row in records:
                handle.write(json.dumps(row, ensure_ascii=False) + os.linesep)

    def _export_parquet_fallback(self, payload: ArtifactExportRequest, path: Path) -> None:
        records = []
        for run_id in payload.run_ids:
            records.extend(self._build_records_for_run(payload, run_id))

        if not records:
            path.write_text("[]", encoding="utf-8")
            return

        try:
            import pandas as pd  # type: ignore
            import pyarrow as pa  # type: ignore
            import pyarrow.parquet as pq  # type: ignore
        except Exception:  # pragma: no cover
            warnings.warn(
                "parquet output unavailable in this runtime. "
                "Install pandas and pyarrow for true parquet export.",
                stacklevel=2,
            )
            fallback = {
                "artifact_id": str(uuid4()),
                "format": ArtifactFormat.PARQUET.value,
                "message": (
                    "parquet output unavailable in this runtime. Install pyarrow and pandas."
                ),
                "run_ids": [str(run_id) for run_id in payload.run_ids],
            }
            with path.open("w", encoding="utf-8") as handle:
                json.dump(fallback, handle, ensure_ascii=False, indent=2)
            return

        frame = pd.DataFrame.from_records(records)
        table = pa.Table.from_pandas(frame, preserve_index=False)
        pq.write_table(table, path)

    def _build_records_for_run(
        self,
        payload: ArtifactExportRequest,
        run_id: str | UUID,
    ) -> list[dict[str, Any]]:
        run = self.run_repository.get(run_id)
        steps = self.trajectory_repository.list_for_run(run_id)
        records: list[dict[str, Any]] = []
        for step in steps:
            records.append(self._build_record(run, payload.split, step))
        return records

    def _build_record(
        self,
        run: RunRecord | None,
        split: str,
        step: TrajectoryStep,
    ) -> dict[str, Any]:
        system_message = None
        if run:
            system_message = (
                f"Run context: project={run.project}, dataset={run.dataset}, "
                f"adapter={run.agent_type.value}"
            )
        return {
            "schema_version": "flight-recorder-jsonl-v1",
            "split": split,
            "format": "chat",
            "run_id": str(step.run_id),
            "project": run.project if run else None,
            "dataset": run.dataset if run else None,
            "agent_type": run.agent_type.value if run else None,
            "step_id": step.id,
            "span_id": step.id,
            "parent_step_id": step.parent_step_id,
            "step_type": step.step_type.value,
            "timestamp": step.started_at.isoformat(),
            "prompt": step.prompt,
            "completion": step.output,
            "input": step.prompt,
            "output": step.output,
            "messages": [
                *([{"role": "system", "content": system_message}] if system_message else []),
                {"role": "user", "content": step.prompt},
                {"role": "assistant", "content": step.output},
            ],
            "reward": 1.0 if step.success else 0.0,
            "label": {
                "success": step.success,
            },
            "metrics": {
                "latency_ms": step.latency_ms,
                "token_usage": step.token_usage,
            },
            "metadata": {
                "model": step.model,
                "temperature": step.temperature,
                "tool_name": step.tool_name,
                "exported_at": datetime.now(UTC).isoformat(),
            },
        }
