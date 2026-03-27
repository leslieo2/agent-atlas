import type {
  EvalJobResponse,
  EvalSampleResultResponse
} from "@/src/shared/api/contract";
import type { EvalJobRecord, EvalSampleResult } from "./model";

export function mapEvalJob(job: EvalJobResponse): EvalJobRecord {
  return {
    evalJobId: job.eval_job_id,
    agentId: job.agent_id,
    dataset: job.dataset,
    project: job.project,
    tags: job.tags,
    scoringMode: job.scoring_mode,
    status: job.status,
    sampleCount: job.sample_count,
    scoredCount: job.scored_count,
    passedCount: job.passed_count,
    failedCount: job.failed_count,
    unscoredCount: job.unscored_count,
    runtimeErrorCount: job.runtime_error_count,
    passRate: job.pass_rate,
    failureDistribution: job.failure_distribution,
    errorCode: job.error_code ?? null,
    errorMessage: job.error_message ?? null,
    createdAt: job.created_at
  };
}

export function mapEvalSample(result: EvalSampleResultResponse): EvalSampleResult {
  return {
    evalJobId: result.eval_job_id,
    datasetSampleId: result.dataset_sample_id,
    runId: result.run_id,
    judgement: result.judgement,
    input: result.input,
    expected: result.expected ?? null,
    actual: result.actual ?? null,
    failureReason: result.failure_reason ?? null,
    errorCode: result.error_code ?? null,
    tags: result.tags
  };
}
