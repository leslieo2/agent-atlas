import { request } from "@/src/shared/api/http";
import { mapEvalJob, type ApiEvalJob } from "./mapper";
import type { CreateEvalJobInput } from "./model";

export async function createEvalJob(payload: CreateEvalJobInput) {
  return mapEvalJob(
    await request<ApiEvalJob>("/api/v1/eval-jobs", {
      method: "POST",
      body: JSON.stringify({
        run_ids: payload.runIds,
        dataset: payload.dataset,
        evaluators: payload.evaluators ?? []
      })
    })
  );
}

