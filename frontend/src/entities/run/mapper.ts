import type { RunResponse as ApiRunRecord } from "@/src/shared/api/contract";
import type { RunRecord } from "./model";

export function mapRun(run: ApiRunRecord): RunRecord {
  return {
    runId: run.run_id,
    inputSummary: run.input_summary,
    status: run.status,
    latencyMs: run.latency_ms,
    tokenCost: run.token_cost,
    toolCalls: run.tool_calls,
    project: run.project,
    dataset: run.dataset ?? null,
    model: run.model,
    agentType: run.agent_type,
    tags: run.tags,
    createdAt: run.created_at,
    projectMetadata: run.project_metadata,
    artifactRef: run.artifact_ref,
    terminationReason: run.termination_reason
  };
}
