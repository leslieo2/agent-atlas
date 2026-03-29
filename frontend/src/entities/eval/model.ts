import type {
  CompareOutcome,
  CurationStatus,
  EvalJobStatus,
  SampleJudgement,
  ScoringMode
} from "@/src/shared/api/contract";
import type { ObservabilityRecord } from "@/src/shared/api/observability";

export interface EvalJobRecord {
  evalJobId: string;
  agentId: string;
  dataset: string;
  project: string;
  tags: string[];
  scoringMode: ScoringMode;
  status: EvalJobStatus;
  sampleCount: number;
  scoredCount: number;
  passedCount: number;
  failedCount: number;
  unscoredCount: number;
  runtimeErrorCount: number;
  passRate: number;
  failureDistribution: Record<string, number>;
  observability?: ObservabilityRecord | null;
  errorCode?: string | null;
  errorMessage?: string | null;
  createdAt: string;
}

export interface EvalSampleRecord {
  evalJobId: string;
  datasetSampleId: string;
  runId: string;
  input: string;
  expected?: string | null;
  actual?: string | null;
  judgement: SampleJudgement;
  compareOutcome?: CompareOutcome | null;
  failureReason?: string | null;
  errorCode?: string | null;
  errorMessage?: string | null;
  tags: string[];
  slice?: string | null;
  source?: string | null;
  exportEligible?: boolean | null;
  curationStatus: CurationStatus;
  curationNote?: string | null;
  publishedAgentSnapshot?: Record<string, unknown> | null;
  artifactRef?: string | null;
  imageRef?: string | null;
  runnerBackend?: string | null;
  latencyMs?: number | null;
  toolCalls?: number | null;
  phoenixTraceUrl?: string | null;
}

export interface CandidateRunSummaryRecord {
  runId: string;
  actual?: string | null;
  traceUrl?: string | null;
}

export interface EvalCompareSampleRecord {
  datasetSampleId: string;
  baselineJudgement?: SampleJudgement | null;
  candidateJudgement?: SampleJudgement | null;
  compareOutcome: CompareOutcome;
  errorCode?: string | null;
  slice?: string | null;
  tags: string[];
  candidateRunSummary?: CandidateRunSummaryRecord | null;
}

export interface EvalCompareRecord {
  baselineEvalJobId: string;
  candidateEvalJobId: string;
  dataset: string;
  distribution: Record<string, number>;
  samples: EvalCompareSampleRecord[];
}

export interface CreateEvalJobInput {
  agentId: string;
  dataset: string;
  project?: string;
  tags?: string[];
  scoringMode?: ScoringMode;
}

export interface EvalSamplePatchInput {
  curationStatus?: CurationStatus | null;
  curationNote?: string | null;
  exportEligible?: boolean | null;
}
