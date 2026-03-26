import type { AgentDescriptorResponse } from "@/src/shared/api/contract";
import type { AgentRecord } from "./model";

export function mapAgent(agent: AgentDescriptorResponse): AgentRecord {
  return {
    agentId: agent.agent_id,
    name: agent.name,
    description: agent.description,
    framework: agent.framework,
    entrypoint: agent.entrypoint,
    defaultModel: agent.default_model,
    tags: agent.tags
  };
}
