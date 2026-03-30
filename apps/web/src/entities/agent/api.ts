import { request } from "@/src/shared/api/http";
import type {
  AgentDescriptorResponse,
  AgentPublicationResponse,
  DiscoveredAgentResponse
} from "@/src/shared/api/contract";
import { mapAgent, mapDiscoveredAgent } from "./mapper";

export async function listPublishedAgents() {
  return (await request<AgentDescriptorResponse[]>("/api/v1/agents/published")).map(mapAgent);
}

export async function listDiscoveredAgents() {
  return (await request<DiscoveredAgentResponse[]>("/api/v1/agents/discovered")).map(mapDiscoveredAgent);
}

export async function publishAgent(agentId: string) {
  return mapAgent(
    await request<AgentDescriptorResponse>(`/api/v1/agents/${agentId}/publish`, {
      method: "POST"
    })
  );
}

export async function unpublishAgent(agentId: string) {
  return request<AgentPublicationResponse>(`/api/v1/agents/${agentId}/unpublish`, {
    method: "POST"
  });
}
