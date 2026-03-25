import type { RunRecord, RunStatus } from "./model";

type ApiRunRecord = {
  run_id: string;
  input_summary: string;
  status: RunStatus;
  latency_ms: number;
  token_cost: number;
  tool_calls: number;
  project: string;
  dataset: string;
  model: string;
  agent_type: string;
  tags: string[];
  created_at: string;
};

export function mapRun(run: ApiRunRecord): RunRecord {
  return {
    runId: run.run_id,
    inputSummary: run.input_summary,
    status: run.status,
    latencyMs: run.latency_ms,
    tokenCost: run.token_cost,
    toolCalls: run.tool_calls,
    project: run.project,
    dataset: run.dataset,
    model: run.model,
    agentType: run.agent_type,
    tags: run.tags,
    createdAt: run.created_at
  };
}

export type { ApiRunRecord };

