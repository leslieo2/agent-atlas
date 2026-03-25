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
  dataset: string;
  model: string;
  agentType: AdapterKind;
  tags: string[];
  createdAt: string;
}

export interface RunListFilters {
  status?: RunStatus;
  project?: string;
  dataset?: string;
  model?: string;
  tag?: string;
  createdFrom?: string;
  createdTo?: string;
}

export interface CreateRunInput {
  project: string;
  dataset: string;
  model: string;
  agentType: AdapterKind;
  inputSummary: string;
  prompt: string;
  tags?: string[];
}
