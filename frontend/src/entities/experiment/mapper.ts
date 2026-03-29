import type {
  CandidateRunSummaryResponse,
  ExperimentCompareResponse,
  ExperimentCompareSampleResponse,
  ExperimentResponse,
  ExperimentRunResponse
} from "@/src/shared/api/contract";
import { mapObservability } from "@/src/shared/api/observability";
import type {
  CandidateRunSummaryRecord,
  ExperimentCompareRecord,
  ExperimentCompareSampleRecord,
  ExperimentRecord,
  ExperimentRunRecord
} from "./model";

export function mapExperiment(record: ExperimentResponse): ExperimentRecord {
  return {
    experimentId: record.experiment_id,
    name: record.name,
    datasetName: record.dataset_name,
    datasetVersionId: record.dataset_version_id,
    publishedAgentId: record.published_agent_id,
    status: record.status,
    tags: record.tags,
    scoringMode: record.spec.evaluator_config?.scoring_mode ?? "exact_match",
    executorBackend: record.spec.executor_config.backend,
    sampleCount: record.sample_count,
    completedCount: record.completed_count,
    passedCount: record.passed_count,
    failedCount: record.failed_count,
    unscoredCount: record.unscored_count,
    runtimeErrorCount: record.runtime_error_count,
    passRate: record.pass_rate,
    failureDistribution: record.failure_distribution,
    observability: mapObservability(record.observability),
    errorCode: record.error_code ?? null,
    errorMessage: record.error_message ?? null,
    createdAt: record.created_at
  };
}

export function mapExperimentRun(record: ExperimentRunResponse): ExperimentRunRecord {
  return {
    runId: record.run_id,
    experimentId: record.experiment_id,
    datasetSampleId: record.dataset_sample_id,
    input: record.input,
    expected: record.expected ?? null,
    actual: record.actual ?? null,
    runStatus: record.run_status as ExperimentRunRecord["runStatus"],
    judgement: record.judgement ?? null,
    compareOutcome: record.compare_outcome ?? null,
    failureReason: record.failure_reason ?? null,
    errorCode: record.error_code ?? null,
    errorMessage: record.error_message ?? null,
    tags: record.tags,
    slice: record.slice ?? null,
    source: record.source ?? null,
    exportEligible: record.export_eligible ?? null,
    curationStatus: record.curation_status,
    curationNote: record.curation_note ?? null,
    publishedAgentSnapshot: record.published_agent_snapshot ?? null,
    artifactRef: record.artifact_ref ?? null,
    imageRef: record.image_ref ?? null,
    executorBackend: record.executor_backend ?? null,
    latencyMs: record.latency_ms ?? null,
    toolCalls: record.tool_calls ?? null,
    phoenixTraceUrl: record.phoenix_trace_url ?? null
  };
}

function mapCandidateRunSummary(summary: CandidateRunSummaryResponse): CandidateRunSummaryRecord {
  return {
    runId: summary.run_id,
    actual: summary.actual ?? null,
    traceUrl: summary.trace_url ?? null
  };
}

function mapCompareSample(sample: ExperimentCompareSampleResponse): ExperimentCompareSampleRecord {
  return {
    datasetSampleId: sample.dataset_sample_id,
    baselineJudgement: sample.baseline_judgement ?? null,
    candidateJudgement: sample.candidate_judgement ?? null,
    compareOutcome: sample.compare_outcome,
    errorCode: sample.error_code ?? null,
    slice: sample.slice ?? null,
    tags: sample.tags,
    candidateRunSummary: sample.candidate_run_summary
      ? mapCandidateRunSummary(sample.candidate_run_summary)
      : null
  };
}

export function mapExperimentCompare(result: ExperimentCompareResponse): ExperimentCompareRecord {
  return {
    baselineExperimentId: result.baseline_experiment_id,
    candidateExperimentId: result.candidate_experiment_id,
    datasetVersionId: result.dataset_version_id,
    distribution: result.distribution,
    samples: result.samples.map(mapCompareSample)
  };
}
