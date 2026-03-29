import { request } from "@/src/shared/api/http";
import type {
  EvalCompareResponse,
  EvalJobCreateRequest,
  EvalJobResponse,
  EvalSampleDetailResponse,
  EvalSamplePatchRequest
} from "@/src/shared/api/contract";
import { mapEvalCompare, mapEvalJob, mapEvalSample } from "./mapper";
import type { CreateEvalJobInput, EvalSamplePatchInput } from "./model";

export async function listEvalJobs() {
  return (await request<EvalJobResponse[]>("/api/v1/eval-jobs")).map(mapEvalJob);
}

export async function listEvalSamples(evalJobId: string) {
  return (await request<EvalSampleDetailResponse[]>(`/api/v1/eval-jobs/${evalJobId}/samples`)).map(mapEvalSample);
}

export async function compareEvalJobs(baselineEvalJobId: string, candidateEvalJobId: string) {
  const params = new URLSearchParams({
    baseline_eval_job_id: baselineEvalJobId,
    candidate_eval_job_id: candidateEvalJobId
  });
  return mapEvalCompare(await request<EvalCompareResponse>(`/api/v1/eval-jobs/compare?${params.toString()}`));
}

export async function patchEvalSample(
  evalJobId: string,
  datasetSampleId: string,
  payload: EvalSamplePatchInput
) {
  const body: EvalSamplePatchRequest = {
    curation_status: payload.curationStatus ?? null,
    curation_note: payload.curationNote ?? null,
    export_eligible: payload.exportEligible ?? null
  };

  return mapEvalSample(
    await request<EvalSampleDetailResponse>(`/api/v1/eval-jobs/${evalJobId}/samples/${datasetSampleId}`, {
      method: "PATCH",
      body: JSON.stringify(body)
    })
  );
}

export async function createEvalJob(payload: CreateEvalJobInput) {
  const body: EvalJobCreateRequest = {
    agent_id: payload.agentId,
    dataset: payload.dataset,
    project: payload.project ?? "rl-eval",
    tags: payload.tags ?? [],
    scoring_mode: payload.scoringMode ?? "exact_match"
  };

  return mapEvalJob(
    await request<EvalJobResponse>("/api/v1/eval-jobs", {
      method: "POST",
      body: JSON.stringify(body)
    })
  );
}
