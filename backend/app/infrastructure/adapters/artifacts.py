from __future__ import annotations

import json
import os
import warnings
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from app.modules.artifacts.domain.models import ArtifactExportRequest, ArtifactMetadata
from app.modules.evals.domain.models import (
    CompareOutcome,
    EvalJobRecord,
    EvalSampleResult,
    SampleJudgement,
)
from app.modules.shared.domain.enums import ArtifactFormat


class _EvalJobReader(Protocol):
    def get(self, eval_job_id: str | UUID) -> EvalJobRecord | None: ...


class _EvalSampleResultReader(Protocol):
    def list_for_job(self, eval_job_id: str | UUID) -> list[EvalSampleResult]: ...


def _compare_outcome(
    baseline: EvalSampleResult | None,
    candidate: EvalSampleResult | None,
) -> CompareOutcome:
    if baseline is None:
        return CompareOutcome.CANDIDATE_ONLY
    if candidate is None:
        return CompareOutcome.BASELINE_ONLY

    if (
        baseline.judgement == SampleJudgement.PASSED
        and candidate.judgement == SampleJudgement.PASSED
    ):
        return CompareOutcome.UNCHANGED_PASS
    if (
        baseline.judgement != SampleJudgement.PASSED
        and candidate.judgement == SampleJudgement.PASSED
    ):
        return CompareOutcome.IMPROVED
    if (
        baseline.judgement == SampleJudgement.PASSED
        and candidate.judgement != SampleJudgement.PASSED
    ):
        return CompareOutcome.REGRESSED
    return CompareOutcome.UNCHANGED_FAIL


class ArtifactExporterAdapter:
    def __init__(
        self,
        artifact_repository,
        eval_job_repository: _EvalJobReader,
        sample_result_repository: _EvalSampleResultReader,
    ) -> None:
        self.artifact_repository = artifact_repository
        self.eval_job_repository = eval_job_repository
        self.sample_result_repository = sample_result_repository
        self.output_dir = Path(__file__).resolve().parents[3] / "data" / "artifacts"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, payload: ArtifactExportRequest) -> ArtifactMetadata:
        source_eval_job_id = payload.candidate_eval_job_id or payload.eval_job_id
        if source_eval_job_id is None:
            raise ValueError("export requires eval_job_id or candidate_eval_job_id")

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
            source_eval_job_id=source_eval_job_id,
            baseline_eval_job_id=payload.baseline_eval_job_id,
            candidate_eval_job_id=payload.candidate_eval_job_id,
            filters_summary=self._filters_summary(payload),
        )
        self.artifact_repository.save(metadata)
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
        if payload.candidate_eval_job_id is not None:
            if self.eval_job_repository.get(payload.candidate_eval_job_id) is None:
                raise ValueError("candidate eval job was not found")
            candidate_results = self.sample_result_repository.list_for_job(
                payload.candidate_eval_job_id
            )
            baseline_results = (
                {
                    result.dataset_sample_id: result
                    for result in self.sample_result_repository.list_for_job(
                        payload.baseline_eval_job_id
                    )
                }
                if payload.baseline_eval_job_id is not None
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
                outcome = _compare_outcome(baseline, candidate)
                if not self._matches_filters(chosen, payload, outcome):
                    continue
                rows.append(self._build_row(chosen, outcome))
            return rows

        if payload.eval_job_id is None or self.eval_job_repository.get(payload.eval_job_id) is None:
            raise ValueError("eval job was not found")
        rows = []
        for result in self.sample_result_repository.list_for_job(payload.eval_job_id):
            if not self._matches_filters(result, payload, None):
                continue
            rows.append(self._build_row(result, None))
        return rows

    def _matches_filters(
        self,
        result: EvalSampleResult,
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
        result: EvalSampleResult,
        compare_outcome: CompareOutcome | None,
    ) -> dict[str, object]:
        snapshot = result.published_agent_snapshot or {}
        manifest = snapshot.get("manifest") if isinstance(snapshot, dict) else {}
        agent_id = manifest.get("agent_id") if isinstance(manifest, dict) else None
        return {
            "schema_version": "rl-export-jsonl-v1",
            "eval_job_id": str(result.eval_job_id),
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
            "runner_backend": result.runner_backend,
            "latency_ms": result.latency_ms,
            "tool_calls": result.tool_calls,
            "phoenix_trace_url": result.trace_url,
            "prompt_version": result.prompt_version,
            "image_digest": result.image_digest,
        }

    @staticmethod
    def _filters_summary(payload: ArtifactExportRequest) -> dict[str, object]:
        return {
            "eval_job_id": str(payload.eval_job_id) if payload.eval_job_id else None,
            "baseline_eval_job_id": (
                str(payload.baseline_eval_job_id) if payload.baseline_eval_job_id else None
            ),
            "candidate_eval_job_id": (
                str(payload.candidate_eval_job_id) if payload.candidate_eval_job_id else None
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
