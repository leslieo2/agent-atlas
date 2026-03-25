import type { EvalJob, EvalResult } from "./model";

type ApiEvalResult = {
  sample_id: string;
  run_id: string;
  input: string;
  status: "pass" | "fail" | "running";
  score: number;
  reason?: string | null;
};

type ApiEvalJob = {
  job_id: string;
  run_ids: string[];
  dataset: string;
  status: string;
  results: ApiEvalResult[];
  created_at: string;
};

export function mapEvalResult(result: ApiEvalResult): EvalResult {
  return {
    sampleId: result.sample_id,
    runId: result.run_id,
    input: result.input,
    status: result.status,
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

export type { ApiEvalJob };

