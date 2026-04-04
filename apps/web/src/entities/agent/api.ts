import { request } from "@/src/shared/api/http";
import type {
  AgentDescriptorResponse,
  AgentValidationRunStartRequest,
  RunResponse
} from "@/src/shared/api/contract";
import { mapAgent } from "./mapper";

export async function listPublishedAgents() {
  return (await request<AgentDescriptorResponse[]>("/api/v1/agents/published")).map(mapAgent);
}

export async function bootstrapClaudeCodeAgent() {
  return mapAgent(
    await request<AgentDescriptorResponse>("/api/v1/agents/bootstrap/claude-code", {
      method: "POST"
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
