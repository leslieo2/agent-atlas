import type {
  AgentDescriptorResponse,
  DiscoveredAgentResponse,
  AgentValidationIssueResponse
} from "@/src/shared/api/contract";
import { mapProvenance } from "@/src/shared/api/provenance";
import type { AgentRecord, AgentValidationIssueRecord, DiscoveredAgentRecord } from "./model";

function mapAgentIssue(issue: AgentValidationIssueResponse): AgentValidationIssueRecord {
  return {
    code: issue.code,
    message: issue.message
  };
}

export function mapAgent(agent: AgentDescriptorResponse): AgentRecord {
  return {
    agentId: agent.agent_id,
    name: agent.name,
    description: agent.description,
    framework: agent.framework,
    entrypoint: agent.entrypoint,
    defaultModel: agent.default_model,
    tags: agent.tags,
    publishedAt: agent.published_at,
    provenance: mapProvenance(agent.provenance)
  };
}

export function mapDiscoveredAgent(agent: DiscoveredAgentResponse): DiscoveredAgentRecord {
  return {
    agentId: agent.agent_id,
    name: agent.name,
    description: agent.description,
    framework: agent.framework,
    entrypoint: agent.entrypoint,
    defaultModel: agent.default_model,
    tags: agent.tags,
    publishState: agent.publish_state,
    validationStatus: agent.validation_status,
    validationIssues: agent.validation_issues.map(mapAgentIssue),
    publishedAt: agent.published_at ?? undefined,
    lastValidatedAt: agent.last_validated_at,
    hasUnpublishedChanges: agent.has_unpublished_changes,
    provenance: mapProvenance(agent.provenance)
  };
}
