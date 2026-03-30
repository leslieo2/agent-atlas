import type {
  CompareOutcome,
  CurationStatus,
  ExperimentStatus,
  RunStatus,
  SampleJudgement,
  ScoringMode
} from "@/src/shared/api/contract";
import type { TracingRecord } from "@/src/shared/api/tracing";

export interface ExperimentRecord {
  experimentId: string;
  name: string;
  datasetName: string;
  datasetVersionId: string;
  publishedAgentId: string;
  status: ExperimentStatus;
  tags: string[];
  scoringMode: ScoringMode;
  executorBackend: string;
  sampleCount: number;
  completedCount: number;
  passedCount: number;
  failedCount: number;
  unscoredCount: number;
  runtimeErrorCount: number;
  passRate: number;
  failureDistribution: Record<string, number>;
  tracing?: TracingRecord | null;
  errorCode?: string | null;
  errorMessage?: string | null;
  createdAt: string;
}

export interface ExperimentRunRecord {
  runId: string;
  experimentId: string;
  datasetSampleId: string;
  input: string;
  expected?: string | null;
  actual?: string | null;
  runStatus: RunStatus;
  judgement?: SampleJudgement | null;
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
  executorBackend?: string | null;
  latencyMs?: number | null;
  toolCalls?: number | null;
  traceUrl?: string | null;
}

export interface CandidateRunSummaryRecord {
  runId: string;
  actual?: string | null;
  traceUrl?: string | null;
}

export interface ExperimentCompareSampleRecord {
  datasetSampleId: string;
  baselineJudgement?: SampleJudgement | null;
  candidateJudgement?: SampleJudgement | null;
  compareOutcome: CompareOutcome;
  errorCode?: string | null;
  slice?: string | null;
  tags: string[];
  candidateRunSummary?: CandidateRunSummaryRecord | null;
}

export interface ExperimentCompareRecord {
  baselineExperimentId: string;
  candidateExperimentId: string;
  datasetVersionId: string;
  distribution: Record<string, number>;
  samples: ExperimentCompareSampleRecord[];
}

export interface CreateExperimentInput {
  name: string;
  datasetVersionId: string;
  publishedAgentId: string;
  model: string;
  scoringMode?: ScoringMode;
  executorBackend?: string;
  runnerImage?: string | null;
  timeoutSeconds?: number;
  maxSteps?: number;
  concurrency?: number;
  promptTemplate?: string | null;
  systemPrompt?: string | null;
  promptVersion?: string | null;
  toolNames?: string[];
  approvalPolicyId?: string | null;
  tags?: string[];
}

export interface ExperimentRunPatchInput {
  curationStatus?: CurationStatus | null;
  curationNote?: string | null;
  exportEligible?: boolean | null;
}
