export type RunStatus = "queued" | "running" | "succeeded" | "failed";

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
  agentType: string;
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
  agentType: string;
  inputSummary: string;
  prompt: string;
  tags?: string[];
}

