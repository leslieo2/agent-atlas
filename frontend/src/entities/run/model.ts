import type { AdapterKind, RunStatus as ApiRunStatus } from "@/src/shared/api/contract";

export type RunStatus = ApiRunStatus;

export interface RunRecord {
  runId: string;
  inputSummary: string;
  status: RunStatus;
  latencyMs: number;
  tokenCost: number;
  toolCalls: number;
  project: string;
  dataset: string | null;
  evalJobId?: string | null;
  datasetSampleId?: string | null;
  agentId: string;
  model: string;
  entrypoint?: string | null;
  agentType: AdapterKind;
  tags: string[];
  createdAt: string;
  projectMetadata?: Record<string, unknown>;
  artifactRef?: string | null;
  executionBackend?: string | null;
  containerImage?: string | null;
  resolvedModel?: string | null;
  errorCode?: string | null;
  errorMessage?: string | null;
  terminationReason?: string | null;
}

export interface RunListFilters {
  status?: RunStatus;
  project?: string;
  dataset?: string;
  agentId?: string;
  model?: string;
  tag?: string;
  createdFrom?: string;
  createdTo?: string;
}

export interface CreateRunInput {
  project: string;
  dataset?: string | null;
  agentId: string;
  inputSummary: string;
  prompt: string;
  tags?: string[];
  projectMetadata?: Record<string, unknown>;
  evalJobId?: string | null;
  datasetSampleId?: string | null;
}

export interface TerminateRunResult {
  runId: string;
  terminated: boolean;
  status: RunStatus;
  terminationReason?: string | null;
}
