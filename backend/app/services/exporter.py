from __future__ import annotations

import json
import os
import warnings
from pathlib import Path
from uuid import uuid4

from app.db.state import state
from app.models.schemas import (
    ArtifactExportRequest,
    ArtifactFormat,
    ArtifactMetadata,
)


class ArtifactExporter:
    def __init__(self) -> None:
        self.output_dir = Path(__file__).resolve().parents[2] / "data" / "artifacts"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, payload: ArtifactExportRequest) -> ArtifactMetadata:
        artifact_id = uuid4()
        extension = payload.format.value
        path = self.output_dir / f"{artifact_id}.{extension}"
        if payload.format == ArtifactFormat.JSONL:
            self._export_jsonl(payload, path)
        else:
            self._export_parquet_fallback(payload, path)
        size_bytes = path.stat().st_size
        metadata = ArtifactMetadata(
            artifact_id=artifact_id,
            format=payload.format,
            run_ids=payload.run_ids,
            path=str(path),
            size_bytes=size_bytes,
        )
        with state.lock:
            state.artifacts[artifact_id] = metadata
            state.save_artifact(metadata)
        return metadata

    def _export_jsonl(self, payload: ArtifactExportRequest, path: Path) -> None:
        records = []
        with state.lock:
            for run_id in payload.run_ids:
                trajectory = state.trajectory.get(run_id, [])
                for step in trajectory:
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
        with path.open("w", encoding="utf-8") as f:
            for row in records:
                f.write(json.dumps(row, ensure_ascii=False) + os.linesep)

    def _export_parquet_fallback(self, payload: ArtifactExportRequest, path: Path) -> None:
        records = []
        with state.lock:
            for run_id in payload.run_ids:
                trajectory = state.trajectory.get(run_id, [])
                for step in trajectory:
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
                    "parquet output unavailable in this runtime. " "Install pyarrow and pandas."
                ),
                "run_ids": [str(rid) for rid in payload.run_ids],
            }
            with path.open("w", encoding="utf-8") as f:
                json.dump(fallback, f, ensure_ascii=False, indent=2)
            return

        frame = pd.DataFrame.from_records(records)
        table = pa.Table.from_pandas(frame, preserve_index=False)
        pq.write_table(table, path)


exporter = ArtifactExporter()
