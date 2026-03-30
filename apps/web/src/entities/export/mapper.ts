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
    sourceExperimentId: record.source_experiment_id ?? null,
    baselineExperimentId: record.baseline_experiment_id ?? null,
    candidateExperimentId: record.candidate_experiment_id ?? null,
    filtersSummary: record.filters_summary
  };
}
