import type { RunResponse as ApiRunRecord } from "@/src/shared/api/contract";
import { mapProvenance } from "@/src/shared/api/provenance";
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
    evalJobId: run.eval_job_id ?? null,
    datasetSampleId: run.dataset_sample_id ?? null,
    agentId: run.agent_id,
    model: run.model,
    entrypoint: run.entrypoint ?? null,
    agentType: run.agent_type,
    tags: run.tags,
    createdAt: run.created_at,
    projectMetadata: run.project_metadata,
    artifactRef: run.artifact_ref,
    executionBackend: run.execution_backend ?? null,
    containerImage: run.container_image ?? null,
    provenance: mapProvenance(run.provenance),
    resolvedModel: run.resolved_model ?? null,
    errorCode: run.error_code ?? null,
    errorMessage: run.error_message ?? null,
    terminationReason: run.termination_reason
  };
}
