from __future__ import annotations

import json
import os
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID, uuid4

from pydantic import ValidationError

from app.modules.agents.domain.models import PublishedAgent
from app.modules.artifacts.application.ports import (
    ArtifactRepository,
    RunLookupSource,
    TrajectoryExportSource,
)
from app.modules.artifacts.domain.models import (
    ArtifactExportRequest,
    ArtifactMetadata,
    ArtifactRunView,
    ArtifactTrajectoryStepView,
)
from app.modules.runs.domain.models import RunRecord, TrajectoryStep
from app.modules.shared.domain.enums import ArtifactFormat


class _RunReader(Protocol):
    def get(self, run_id: str | UUID) -> RunRecord | None: ...


class _TrajectoryReader(Protocol):
    def list_for_run(self, run_id: str | UUID) -> list[TrajectoryStep]: ...


class RunArtifactExportSourceAdapter(RunLookupSource):
    def __init__(self, run_repository: _RunReader) -> None:
        self.run_repository = run_repository

    def get(self, run_id: str | UUID) -> ArtifactRunView | None:
        run = self.run_repository.get(run_id)
        if run is None:
            return None

        return ArtifactRunView(
            run_id=run.run_id,
            project=run.project,
            dataset=run.dataset,
            agent_id=run.agent_id,
            entrypoint=run.entrypoint,
            resolved_model=run.resolved_model,
            agent_type=run.agent_type,
            project_metadata=run.project_metadata,
            provenance=run.provenance,
        )


class TrajectoryArtifactExportSourceAdapter(TrajectoryExportSource):
    def __init__(self, trajectory_repository: _TrajectoryReader) -> None:
        self.trajectory_repository = trajectory_repository

    def list_for_run(self, run_id: str | UUID) -> list[ArtifactTrajectoryStepView]:
        return [
            ArtifactTrajectoryStepView(
                id=step.id,
                run_id=step.run_id,
                step_type=step.step_type,
                parent_step_id=step.parent_step_id,
                prompt=step.prompt,
                output=step.output,
                model=step.model,
                temperature=step.temperature,
                latency_ms=step.latency_ms,
                token_usage=step.token_usage,
                success=step.success,
                tool_name=step.tool_name,
                started_at=step.started_at,
            )
            for step in self.trajectory_repository.list_for_run(run_id)
        ]


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
        run: ArtifactRunView | None,
        split: str,
        step: ArtifactTrajectoryStepView,
    ) -> dict[str, Any]:
        system_message = None
        if run:
            system_message = (
                f"Run context: project={run.project}, dataset={run.dataset}, "
                f"adapter={run.agent_type.value}"
            )
        published_agent = self._published_agent_summary(run)
        return {
            "schema_version": "flight-recorder-jsonl-v1",
            "split": split,
            "format": "chat",
            "run_id": str(step.run_id),
            "project": run.project if run else None,
            "dataset": run.dataset if run else None,
            "agent_id": run.agent_id if run else None,
            "entrypoint": run.entrypoint if run else None,
            "resolved_model": run.resolved_model if run else None,
            "published_agent_snapshot": run.provenance.published_agent_snapshot
            if run and run.provenance
            else None,
            "published_agent": published_agent,
            "agent_type": run.agent_type.value if run else None,
            "artifact_ref": run.provenance.artifact_ref if run and run.provenance else None,
            "image_ref": run.provenance.image_ref if run and run.provenance else None,
            "trace_backend": run.provenance.trace_backend if run and run.provenance else None,
            "runner_backend": run.provenance.runner_backend if run and run.provenance else None,
            "eval_job_id": (
                str(run.provenance.eval_job_id)
                if run and run.provenance and run.provenance.eval_job_id
                else None
            ),
            "dataset_sample_id": run.provenance.dataset_sample_id
            if run and run.provenance
            else None,
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

    @staticmethod
    def _published_agent_summary(run: ArtifactRunView | None) -> dict[str, Any] | None:
        if run is None or run.provenance is None:
            return None

        raw_snapshot = run.provenance.published_agent_snapshot
        if not isinstance(raw_snapshot, dict):
            return None

        try:
            snapshot = PublishedAgent.model_validate(raw_snapshot)
        except ValidationError:
            return None

        return {
            "published_at": snapshot.published_at.isoformat().replace("+00:00", "Z"),
            "default_model": snapshot.default_model,
            "tags": snapshot.tags,
        }
