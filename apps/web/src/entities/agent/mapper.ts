import type {
  AgentDescriptorResponse,
  DiscoveredAgentResponse,
  AgentValidationIssueResponse,
  ExecutionReference
} from "@/src/shared/api/contract";
import type {
  AgentRecord,
  AgentValidationIssueRecord,
  DiscoveredAgentRecord,
  ExecutionReferenceRecord
} from "./model";

function mapAgentIssue(issue: AgentValidationIssueResponse): AgentValidationIssueRecord {
  return {
    code: issue.code,
    message: issue.message
  };
}

function mapExecutionReference(executionReference?: ExecutionReference | null): ExecutionReferenceRecord | null {
  if (!executionReference) {
    return null;
  }

  return {
    artifactRef: executionReference.artifact_ref ?? null,
    imageRef: executionReference.image_ref ?? null
  };
}

export function mapAgent(agent: AgentDescriptorResponse): AgentRecord {
  return {
    agentId: agent.agent_id,
    name: agent.name,
    description: agent.description,
    framework: agent.framework,
    frameworkVersion: agent.framework_version,
    entrypoint: agent.entrypoint,
    defaultModel: agent.default_model,
    tags: agent.tags,
    capabilities: agent.capabilities,
    publishedAt: agent.published_at,
    sourceFingerprint: agent.source_fingerprint ?? undefined,
    executionReference: mapExecutionReference(agent.execution_reference),
    defaultRuntimeProfile: agent.default_runtime_profile
  };
}

export function mapDiscoveredAgent(agent: DiscoveredAgentResponse): DiscoveredAgentRecord {
  return {
    agentId: agent.agent_id,
    name: agent.name,
    description: agent.description,
    framework: agent.framework,
    frameworkVersion: agent.framework_version,
    entrypoint: agent.entrypoint,
    defaultModel: agent.default_model,
    tags: agent.tags,
    capabilities: agent.capabilities,
    publishState: agent.publish_state,
    validationStatus: agent.validation_status,
    validationIssues: agent.validation_issues.map(mapAgentIssue),
    publishedAt: agent.published_at ?? undefined,
    lastValidatedAt: agent.last_validated_at,
    hasUnpublishedChanges: agent.has_unpublished_changes,
    sourceFingerprint: agent.source_fingerprint ?? undefined,
    executionReference: mapExecutionReference(agent.execution_reference),
    defaultRuntimeProfile: agent.default_runtime_profile
  };
}
