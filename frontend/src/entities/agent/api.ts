import { request } from "@/src/shared/api/http";
import type { AgentDescriptorResponse } from "@/src/shared/api/contract";
import { mapAgent } from "./mapper";

export async function listAgents() {
  return (await request<AgentDescriptorResponse[]>("/api/v1/agents")).map(mapAgent);
}
