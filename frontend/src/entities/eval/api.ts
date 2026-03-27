import { request } from "@/src/shared/api/http";
import type {
  EvalJobCreateRequest,
  EvalJobResponse,
  EvalSampleResultResponse
} from "@/src/shared/api/contract";
import { mapEvalJob, mapEvalSample } from "./mapper";
import type { CreateEvalJobInput } from "./model";

export async function listEvalJobs() {
  return (await request<EvalJobResponse[]>("/api/v1/eval-jobs")).map(mapEvalJob);
}

export async function listEvalSamples(evalJobId: string) {
  return (await request<EvalSampleResultResponse[]>(`/api/v1/eval-jobs/${evalJobId}/samples`)).map(mapEvalSample);
}

export async function createEvalJob(payload: CreateEvalJobInput) {
  const body: EvalJobCreateRequest = {
    agent_id: payload.agentId,
    dataset: payload.dataset,
    project: payload.project,
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
