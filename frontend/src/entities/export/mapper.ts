import type { ExportMetadataResponse } from "@/src/shared/api/contract";
import type { ExportRecord } from "./model";

export function mapExportRecord(record: ExportMetadataResponse): ExportRecord {
  return {
    exportId: record.export_id,
    format: record.format,
    createdAt: record.created_at,
    path: record.path,
    sizeBytes: record.size_bytes,
    rowCount: record.row_count,
    sourceEvalJobId: record.source_eval_job_id ?? null,
    baselineEvalJobId: record.baseline_eval_job_id ?? null,
    candidateEvalJobId: record.candidate_eval_job_id ?? null,
    filtersSummary: record.filters_summary
  };
}
