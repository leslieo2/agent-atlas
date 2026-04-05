import { request } from "@/src/shared/api/http";
import type {
  AgentDescriptorResponse,
  AgentImportRequest,
  AgentValidationRunStartRequest,
  RunResponse
} from "@/src/shared/api/contract";
import { mapAgent } from "./mapper";
import type { ImportAgentInput } from "./model";

export async function listPublishedAgents() {
  return (await request<AgentDescriptorResponse[]>("/api/v1/agents/published")).map(mapAgent);
}

export async function createClaudeCodeBridgeAsset() {
  return mapAgent(
    await request<AgentDescriptorResponse>("/api/v1/agents/starters/claude-code", {
      method: "POST"
    })
  );
}

export async function importAgent(input: ImportAgentInput) {
  const payload: AgentImportRequest = {
    agent_id: input.agentId,
    name: input.name,
    description: input.description,
    framework: input.framework,
    default_model: input.defaultModel,
    entrypoint: input.entrypoint,
    agent_family: input.agentFamily ?? null,
    framework_version: input.frameworkVersion ?? "1.0.0",
    tags: input.tags ?? [],
    capabilities: input.capabilities ?? []
  };

  return mapAgent(
    await request<AgentDescriptorResponse>("/api/v1/agents/imports", {
      method: "POST",
      body: JSON.stringify(payload)
    })
  );
}

export async function startValidationRun(
  agentId: string,
  payload: AgentValidationRunStartRequest
) {
  return request<RunResponse>(`/api/v1/agents/${agentId}/validation-runs`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
