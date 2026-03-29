import type {
  CandidateRunSummaryResponse,
  EvalCompareResponse,
  EvalCompareSampleResponse,
  EvalJobResponse,
  EvalSampleDetailResponse
} from "@/src/shared/api/contract";
import { mapObservability } from "@/src/shared/api/observability";
import type {
  CandidateRunSummaryRecord,
  EvalCompareRecord,
  EvalCompareSampleRecord,
  EvalJobRecord,
  EvalSampleRecord
} from "./model";

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
    observability: mapObservability(job.observability),
    errorCode: job.error_code ?? null,
    errorMessage: job.error_message ?? null,
    createdAt: job.created_at
  };
}

export function mapEvalSample(result: EvalSampleDetailResponse): EvalSampleRecord {
  return {
    evalJobId: result.eval_job_id,
    datasetSampleId: result.dataset_sample_id,
    runId: result.run_id,
    input: result.input,
    expected: result.expected ?? null,
    actual: result.actual ?? null,
    judgement: result.judgement,
    compareOutcome: result.compare_outcome ?? null,
    failureReason: result.failure_reason ?? null,
    errorCode: result.error_code ?? null,
    errorMessage: result.error_message ?? null,
    tags: result.tags,
    slice: result.slice ?? null,
    source: result.source ?? null,
    exportEligible: result.export_eligible ?? null,
    curationStatus: result.curation_status,
    curationNote: result.curation_note ?? null,
    publishedAgentSnapshot: result.published_agent_snapshot ?? null,
    artifactRef: result.artifact_ref ?? null,
    imageRef: result.image_ref ?? null,
    runnerBackend: result.runner_backend ?? null,
    latencyMs: result.latency_ms ?? null,
    toolCalls: result.tool_calls ?? null,
    phoenixTraceUrl: result.phoenix_trace_url ?? null
  };
}

function mapCandidateRunSummary(summary: CandidateRunSummaryResponse): CandidateRunSummaryRecord {
  return {
    runId: summary.run_id,
    actual: summary.actual ?? null,
    traceUrl: summary.trace_url ?? null
  };
}

function mapCompareSample(sample: EvalCompareSampleResponse): EvalCompareSampleRecord {
  return {
    datasetSampleId: sample.dataset_sample_id,
    baselineJudgement: sample.baseline_judgement ?? null,
    candidateJudgement: sample.candidate_judgement ?? null,
    compareOutcome: sample.compare_outcome,
    errorCode: sample.error_code ?? null,
    slice: sample.slice ?? null,
    tags: sample.tags,
    candidateRunSummary: sample.candidate_run_summary ? mapCandidateRunSummary(sample.candidate_run_summary) : null
  };
}

export function mapEvalCompare(result: EvalCompareResponse): EvalCompareRecord {
  return {
    baselineEvalJobId: result.baseline_eval_job_id,
    candidateEvalJobId: result.candidate_eval_job_id,
    dataset: result.dataset,
    distribution: result.distribution,
    samples: result.samples.map(mapCompareSample)
  };
}
