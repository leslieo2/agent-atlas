import type { EvalJobResponse as ApiEvalJob, EvalResultResponse as ApiEvalResult } from "@/src/shared/api/contract";
import type { EvalJob, EvalResult } from "./model";

function normalizeEvalResultStatus(status: ApiEvalResult["status"]): EvalResult["status"] {
  if (status === "pass" || status === "fail" || status === "running") {
    return status;
  }
  return "running";
}

export function mapEvalResult(result: ApiEvalResult): EvalResult {
  return {
    sampleId: result.sample_id,
    runId: result.run_id,
    input: result.input,
    status: normalizeEvalResultStatus(result.status),
    score: result.score,
    reason: result.reason
  };
}

export function mapEvalJob(job: ApiEvalJob): EvalJob {
  return {
    jobId: job.job_id,
    runIds: job.run_ids,
    dataset: job.dataset,
    status: job.status,
    results: job.results.map(mapEvalResult),
    createdAt: job.created_at
  };
}
