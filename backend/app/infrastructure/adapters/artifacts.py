from __future__ import annotations

import json
import os
import warnings
from pathlib import Path
from uuid import uuid4

from app.modules.artifacts.application.ports import ArtifactRepository, TrajectoryExportSource
from app.modules.artifacts.domain.models import ArtifactExportRequest, ArtifactMetadata
from app.modules.shared.domain.enums import ArtifactFormat


class ArtifactExporterAdapter:
    def __init__(
        self,
        trajectory_repository: TrajectoryExportSource,
        artifact_repository: ArtifactRepository,
    ) -> None:
        self.trajectory_repository = trajectory_repository
        self.artifact_repository = artifact_repository
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
            for step in self.trajectory_repository.list_for_run(run_id):
                records.append(
                    {
                        "run_id": str(run_id),
                        "span_id": step.id,
                        "step_type": step.step_type.value,
                        "input": step.prompt,
                        "output": step.output,
                        "latency_ms": step.latency_ms,
                        "token_usage": step.token_usage,
                        "tool_name": step.tool_name,
                    }
                )
        with path.open("w", encoding="utf-8") as handle:
            for row in records:
                handle.write(json.dumps(row, ensure_ascii=False) + os.linesep)

    def _export_parquet_fallback(self, payload: ArtifactExportRequest, path: Path) -> None:
        records = []
        for run_id in payload.run_ids:
            for step in self.trajectory_repository.list_for_run(run_id):
                records.append(
                    {
                        "run_id": str(run_id),
                        "span_id": step.id,
                        "step_type": step.step_type.value,
                        "input": step.prompt,
                        "output": step.output,
                        "latency_ms": step.latency_ms,
                        "token_usage": step.token_usage,
                        "tool_name": step.tool_name,
                    }
                )

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
