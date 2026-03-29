import type { EvalJobStatus, SampleJudgement, ScoringMode } from "@/src/shared/api/contract";
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

export interface EvalSampleResult {
  evalJobId: string;
  datasetSampleId: string;
  runId: string;
  judgement: SampleJudgement;
  input: string;
  expected?: string | null;
  actual?: string | null;
  failureReason?: string | null;
  errorCode?: string | null;
  traceUrl?: string | null;
  tags: string[];
}

export interface CreateEvalJobInput {
  agentId: string;
  dataset: string;
  project: string;
  tags?: string[];
  scoringMode?: ScoringMode;
}
