import type {
  AgentDescriptorResponse,
  DiscoveredAgentResponse,
  AgentValidationIssueResponse,
  RuntimeArtifactMetadata
} from "@/src/shared/api/contract";
import { mapProvenance } from "@/src/shared/api/provenance";
import type {
  AgentRecord,
  AgentValidationIssueRecord,
  DiscoveredAgentRecord,
  RuntimeArtifactRecord
} from "./model";

function mapAgentIssue(issue: AgentValidationIssueResponse): AgentValidationIssueRecord {
  return {
    code: issue.code,
    message: issue.message
  };
}

function mapRuntimeArtifact(runtimeArtifact?: RuntimeArtifactMetadata | null): RuntimeArtifactRecord | null {
  if (!runtimeArtifact) {
    return null;
  }

  return {
    buildStatus: runtimeArtifact.build_status ?? null,
    sourceFingerprint: runtimeArtifact.source_fingerprint ?? null,
    framework: runtimeArtifact.framework ?? null,
    entrypoint: runtimeArtifact.entrypoint ?? null,
    artifactRef: runtimeArtifact.artifact_ref ?? null,
    imageRef: runtimeArtifact.image_ref ?? null
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
    runtimeArtifact: mapRuntimeArtifact(agent.runtime_artifact),
    provenance: mapProvenance(agent.provenance)
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
    runtimeArtifact: mapRuntimeArtifact(agent.runtime_artifact),
    provenance: mapProvenance(agent.provenance)
  };
}
