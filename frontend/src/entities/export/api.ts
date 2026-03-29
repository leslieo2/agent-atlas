import { getApiBaseUrl } from "@/src/shared/config/env";
import { request } from "@/src/shared/api/http";
import type { ExportCreateRequest, ExportMetadataResponse } from "@/src/shared/api/contract";
import { mapExportRecord } from "./mapper";
import type { CreateExportInput } from "./model";

export async function listExports() {
  return (await request<ExportMetadataResponse[]>("/api/v1/exports")).map(mapExportRecord);
}

export async function createExport(payload: CreateExportInput) {
  const body: ExportCreateRequest = {
    eval_job_id: payload.evalJobId ?? null,
    baseline_eval_job_id: payload.baselineEvalJobId ?? null,
    candidate_eval_job_id: payload.candidateEvalJobId ?? null,
    dataset_sample_ids: payload.datasetSampleIds ?? null,
    judgements: payload.judgements ?? null,
    error_codes: payload.errorCodes ?? null,
    compare_outcomes: payload.compareOutcomes ?? null,
    tags: payload.tags ?? null,
    slices: payload.slices ?? null,
    curation_statuses: payload.curationStatuses ?? null,
    export_eligible: payload.exportEligible ?? null,
    format: payload.format ?? "jsonl"
  };

  return mapExportRecord(
    await request<ExportMetadataResponse>("/api/v1/exports", {
      method: "POST",
      body: JSON.stringify(body)
    })
  );
}

export function getExportDownloadUrl(exportId: string) {
  return `${getApiBaseUrl()}/api/v1/exports/${exportId}`;
}
