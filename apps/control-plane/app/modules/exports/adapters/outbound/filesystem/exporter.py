from __future__ import annotations

import json
import os
import warnings
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from app.modules.experiments.domain.compare import compare_outcome
from app.modules.experiments.domain.models import ExperimentRecord, RunEvaluationRecord
from app.modules.exports.domain.models import ArtifactExportRequest, ArtifactMetadata
from app.modules.shared.domain.enums import ArtifactFormat, CompareOutcome


class _ExperimentReader(Protocol):
    def get(self, experiment_id: str | UUID) -> ExperimentRecord | None: ...


class _RunEvaluationReader(Protocol):
    def list_for_experiment(self, experiment_id: str | UUID) -> list[RunEvaluationRecord]: ...


class ExporterAdapter:
    def __init__(
        self,
        export_repository,
        experiment_repository: _ExperimentReader,
        run_evaluation_repository: _RunEvaluationReader,
    ) -> None:
        self.export_repository = export_repository
        self.experiment_repository = experiment_repository
        self.run_evaluation_repository = run_evaluation_repository
        app_root = Path(__file__).resolve()
        while app_root.name != "app":
            app_root = app_root.parent
        self.output_dir = app_root.parent / "data" / "exports"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, payload: ArtifactExportRequest) -> ArtifactMetadata:
        source_experiment_id = payload.candidate_experiment_id or payload.experiment_id
        if source_experiment_id is None:
            raise ValueError("export requires experiment_id or candidate_experiment_id")

        rows = self._build_rows(payload)
        artifact_id = uuid4()
        extension = payload.format.value
        path = self.output_dir / f"{artifact_id}.{extension}"
        if payload.format == ArtifactFormat.JSONL:
            self._write_jsonl(rows, path)
        else:
            self._write_parquet(rows, path)

        metadata = ArtifactMetadata(
            artifact_id=artifact_id,
            format=payload.format,
            path=str(path),
            size_bytes=path.stat().st_size,
            row_count=len(rows),
            source_experiment_id=source_experiment_id,
            baseline_experiment_id=payload.baseline_experiment_id,
            candidate_experiment_id=payload.candidate_experiment_id,
            filters_summary=self._filters_summary(payload),
        )
        self.export_repository.save(metadata)
        return metadata

    def _write_jsonl(self, rows: list[dict[str, object]], path: Path) -> None:
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + os.linesep)

    def _write_parquet(self, rows: list[dict[str, object]], path: Path) -> None:
        if not rows:
            path.write_text("[]", encoding="utf-8")
            return

        try:
            import pandas as pd  # type: ignore
            import pyarrow as pa  # type: ignore
            import pyarrow.parquet as pq  # type: ignore
        except Exception:
            warnings.warn(
                (
                    "parquet output unavailable in this runtime. "
                    "Install pandas and pyarrow for true parquet export."
                ),
                stacklevel=2,
            )
            with path.open("w", encoding="utf-8") as handle:
                json.dump(rows, handle, ensure_ascii=False, indent=2)
            return

        frame = pd.DataFrame.from_records(rows)
        table = pa.Table.from_pandas(frame, preserve_index=False)
        pq.write_table(table, path)

    def _build_rows(self, payload: ArtifactExportRequest) -> list[dict[str, object]]:
        if payload.candidate_experiment_id is not None:
            if self.experiment_repository.get(payload.candidate_experiment_id) is None:
                raise ValueError("candidate experiment was not found")
            candidate_results = self.run_evaluation_repository.list_for_experiment(
                payload.candidate_experiment_id
            )
            baseline_results = (
                {
                    result.dataset_sample_id: result
                    for result in self.run_evaluation_repository.list_for_experiment(
                        payload.baseline_experiment_id
                    )
                }
                if payload.baseline_experiment_id is not None
                else {}
            )
            rows: list[dict[str, object]] = []
            candidate_by_sample = {result.dataset_sample_id: result for result in candidate_results}
            sample_ids = sorted(set(candidate_by_sample) | set(baseline_results))
            for sample_id in sample_ids:
                candidate = candidate_by_sample.get(sample_id)
                baseline = baseline_results.get(sample_id)
                chosen = candidate or baseline
                if chosen is None:
                    continue
                outcome = compare_outcome(baseline, candidate)
                if not self._matches_filters(chosen, payload, outcome):
                    continue
                rows.append(self._build_row(chosen, outcome))
            return rows

        if (
            payload.experiment_id is None
            or self.experiment_repository.get(payload.experiment_id) is None
        ):
            raise ValueError("experiment was not found")
        rows = []
        for result in self.run_evaluation_repository.list_for_experiment(payload.experiment_id):
            if not self._matches_filters(result, payload, None):
                continue
            rows.append(self._build_row(result, None))
        return rows

    def _matches_filters(
        self,
        result: RunEvaluationRecord,
        payload: ArtifactExportRequest,
        compare_outcome: CompareOutcome | None,
    ) -> bool:
        if payload.dataset_sample_ids and result.dataset_sample_id not in set(
            payload.dataset_sample_ids
        ):
            return False
        if payload.judgements and result.judgement.value not in set(payload.judgements):
            return False
        if payload.error_codes and (result.error_code or "") not in set(payload.error_codes):
            return False
        if payload.compare_outcomes and (
            compare_outcome is None or compare_outcome.value not in set(payload.compare_outcomes)
        ):
            return False
        if payload.tags and not set(payload.tags).intersection(result.tags):
            return False
        if payload.slices and (result.slice or "") not in set(payload.slices):
            return False
        if payload.curation_statuses and result.curation_status.value not in set(
            payload.curation_statuses
        ):
            return False
        return not (
            payload.export_eligible is not None
            and result.export_eligible != payload.export_eligible
        )

    def _build_row(
        self,
        result: RunEvaluationRecord,
        compare_outcome: CompareOutcome | None,
    ) -> dict[str, object]:
        snapshot = result.published_agent_snapshot or {}
        manifest = snapshot.get("manifest") if isinstance(snapshot, dict) else {}
        agent_id = manifest.get("agent_id") if isinstance(manifest, dict) else None
        return {
            "schema_version": "rl-export-jsonl-v1",
            "experiment_id": str(result.experiment_id),
            "dataset_version_id": str(result.dataset_version_id),
            "run_id": str(result.run_id),
            "dataset_sample_id": result.dataset_sample_id,
            "input": result.input,
            "expected": result.expected,
            "actual": result.actual,
            "judgement": result.judgement.value,
            "compare_outcome": compare_outcome.value if compare_outcome else None,
            "failure_reason": result.failure_reason,
            "error_code": result.error_code,
            "error_message": result.error_message,
            "tags": result.tags,
            "dataset_slice": result.slice,
            "dataset_source": result.source,
            "export_eligible": result.export_eligible,
            "curation_status": result.curation_status.value,
            "curation_note": result.curation_note,
            "published_agent_snapshot": result.published_agent_snapshot,
            "agent_id": agent_id,
            "framework": result.framework,
            "artifact_ref": result.artifact_ref,
            "image_ref": result.image_ref,
            "executor_backend": result.executor_backend,
            "latency_ms": result.latency_ms,
            "tool_calls": result.tool_calls,
            "trace_url": result.trace_url,
            "prompt_version": result.prompt_version,
            "image_digest": result.image_digest,
        }

    @staticmethod
    def _filters_summary(payload: ArtifactExportRequest) -> dict[str, object]:
        return {
            "experiment_id": str(payload.experiment_id) if payload.experiment_id else None,
            "baseline_experiment_id": (
                str(payload.baseline_experiment_id) if payload.baseline_experiment_id else None
            ),
            "candidate_experiment_id": (
                str(payload.candidate_experiment_id) if payload.candidate_experiment_id else None
            ),
            "dataset_sample_ids": payload.dataset_sample_ids,
            "judgements": payload.judgements,
            "error_codes": payload.error_codes,
            "compare_outcomes": payload.compare_outcomes,
            "tags": payload.tags,
            "slices": payload.slices,
            "curation_statuses": payload.curation_statuses,
            "export_eligible": payload.export_eligible,
        }
