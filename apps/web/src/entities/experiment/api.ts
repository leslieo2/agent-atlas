import { request } from "@/src/shared/api/http";
import type {
  ExperimentCompareResponse,
  ExperimentCreateRequest,
  ExperimentResponse,
  ExperimentRunResponse,
  RunEvaluationPatchRequest
} from "@/src/shared/api/contract";
import { mapExperiment, mapExperimentCompare, mapExperimentRun } from "./mapper";
import type { CreateExperimentInput, ExperimentRunPatchInput } from "./model";

export async function listExperiments() {
  return (await request<ExperimentResponse[]>("/api/v1/experiments")).map(mapExperiment);
}

export async function getExperiment(experimentId: string) {
  return mapExperiment(await request<ExperimentResponse>(`/api/v1/experiments/${experimentId}`));
}

export async function createExperiment(payload: CreateExperimentInput) {
  const body: ExperimentCreateRequest = {
    name: payload.name,
    spec: {
      dataset_version_id: payload.datasetVersionId,
      published_agent_id: payload.publishedAgentId,
      model_settings: {
        model: payload.model,
        temperature: 0
      },
      prompt_config: {
        prompt_template: payload.promptTemplate ?? null,
        system_prompt: payload.systemPrompt ?? null,
        prompt_version: payload.promptVersion ?? null
      },
      toolset_config: {
        tools: payload.toolNames ?? [],
        metadata: {}
      },
      evaluator_config: {
        scoring_mode: payload.scoringMode ?? "exact_match",
        metadata: {}
      },
      approval_policy_id: payload.approvalPolicyId ?? null,
      tags: payload.tags ?? []
    }
  };

  return mapExperiment(
    await request<ExperimentResponse>("/api/v1/experiments", {
      method: "POST",
      body: JSON.stringify(body)
    })
  );
}

export async function startExperiment(experimentId: string) {
  return mapExperiment(
    await request<ExperimentResponse>(`/api/v1/experiments/${experimentId}/start`, {
      method: "POST"
    })
  );
}

export async function cancelExperiment(experimentId: string) {
  return mapExperiment(
    await request<ExperimentResponse>(`/api/v1/experiments/${experimentId}/cancel`, {
      method: "POST"
    })
  );
}

export async function listExperimentRuns(experimentId: string) {
  return (await request<ExperimentRunResponse[]>(`/api/v1/experiments/${experimentId}/runs`)).map(
    mapExperimentRun
  );
}

export async function compareExperiments(baselineExperimentId: string, candidateExperimentId: string) {
  const params = new URLSearchParams({
    baseline_experiment_id: baselineExperimentId,
    candidate_experiment_id: candidateExperimentId
  });
  return mapExperimentCompare(
    await request<ExperimentCompareResponse>(`/api/v1/experiments/compare?${params.toString()}`)
  );
}

export async function patchExperimentRun(
  experimentId: string,
  runId: string,
  payload: ExperimentRunPatchInput
) {
  const body: RunEvaluationPatchRequest = {
    curation_status: payload.curationStatus ?? null,
    curation_note: payload.curationNote ?? null,
    export_eligible: payload.exportEligible ?? null
  };

  return mapExperimentRun(
    await request<ExperimentRunResponse>(`/api/v1/experiments/${experimentId}/runs/${runId}`, {
      method: "PATCH",
      body: JSON.stringify(body)
    })
  );
}
