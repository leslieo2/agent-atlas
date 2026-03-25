import { request } from "@/src/shared/api/http";
import type { EvalJobCreate, EvalJobResponse } from "@/src/shared/api/contract";
import { mapEvalJob } from "./mapper";
import type { CreateEvalJobInput } from "./model";

export async function createEvalJob(payload: CreateEvalJobInput) {
  const body: EvalJobCreate = {
    run_ids: payload.runIds,
    dataset: payload.dataset,
    evaluators: payload.evaluators ?? []
  };

  return mapEvalJob(
    await request<EvalJobResponse>("/api/v1/eval-jobs", {
      method: "POST",
      body: JSON.stringify(body)
    })
  );
}

export async function getEvalJob(jobId: string) {
  return mapEvalJob(await request<EvalJobResponse>(`/api/v1/eval-jobs/${jobId}`));
}
