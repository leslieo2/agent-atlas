import { request } from "@/src/shared/api/http";
import type { RunCreateRequest, RunResponse, TerminateRunResponse } from "@/src/shared/api/contract";
import { mapRun } from "./mapper";
import type { CreateRunInput, RunListFilters, TerminateRunResult } from "./model";

export async function listRuns(filters: RunListFilters = {}) {
  const query = new URLSearchParams();

  if (filters.status) query.set("status", filters.status);
  if (filters.project) query.set("project", filters.project);
  if (filters.dataset) query.set("dataset", filters.dataset);
  if (filters.model) query.set("model", filters.model);
  if (filters.tag) query.set("tag", filters.tag);
  if (filters.createdFrom) query.set("created_from", filters.createdFrom);
  if (filters.createdTo) query.set("created_to", filters.createdTo);

  const suffix = query.toString();
  const path = suffix ? `/api/v1/runs?${suffix}` : "/api/v1/runs";

  return (await request<RunResponse[]>(path)).map(mapRun);
}

export async function createRun(payload: CreateRunInput) {
  const body: RunCreateRequest = {
    project: payload.project,
    dataset: payload.dataset ?? null,
    model: payload.model,
    agent_type: payload.agentType,
    input_summary: payload.inputSummary,
    prompt: payload.prompt,
    tags: payload.tags ?? [],
    tool_config: payload.toolConfig ?? {},
    project_metadata: payload.projectMetadata ?? {}
  };

  return mapRun(
    await request<RunResponse>("/api/v1/runs", {
      method: "POST",
      body: JSON.stringify(body)
    })
  );
}

export async function getRun(runId: string) {
  return mapRun(await request<RunResponse>(`/api/v1/runs/${runId}`));
}

export async function terminateRun(runId: string): Promise<TerminateRunResult> {
  const response = await request<TerminateRunResponse>(`/api/v1/runs/${runId}/terminate`, {
    method: "POST"
  });

  return {
    runId: response.run_id,
    terminated: response.terminated,
    status: response.status,
    terminationReason: response.termination_reason
  };
}
