import type {
  AgentDescriptorResponse,
  AgentValidationEvidenceSummaryResponse,
  DiscoveredAgentResponse,
  AgentValidationIssueResponse,
  AgentValidationOutcomeSummaryResponse,
  AgentValidationRunReferenceResponse,
  ExecutionReference
} from "@/src/shared/api/contract";
import type {
  AgentRecord,
  AgentValidationEvidenceSummaryRecord,
  AgentValidationIssueRecord,
  AgentValidationOutcomeSummaryRecord,
  AgentValidationRunReferenceRecord,
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

function mapValidationRunReference(
  validationRun?: AgentValidationRunReferenceResponse | null
): AgentValidationRunReferenceRecord | null {
  if (!validationRun) {
    return null;
  }

  return {
    runId: validationRun.run_id,
    status: validationRun.status,
    createdAt: validationRun.created_at,
    startedAt: validationRun.started_at ?? null,
    completedAt: validationRun.completed_at ?? null
  };
}

function mapValidationEvidence(
  validationEvidence?: AgentValidationEvidenceSummaryResponse | null
): AgentValidationEvidenceSummaryRecord | null {
  if (!validationEvidence) {
    return null;
  }

  return {
    artifactRef: validationEvidence.artifact_ref ?? null,
    imageRef: validationEvidence.image_ref ?? null,
    traceUrl: validationEvidence.trace_url ?? null,
    terminalSummary: validationEvidence.terminal_summary ?? null
  };
}

function mapValidationOutcome(
  validationOutcome?: AgentValidationOutcomeSummaryResponse | null
): AgentValidationOutcomeSummaryRecord | null {
  if (!validationOutcome) {
    return null;
  }

  return {
    status: validationOutcome.status,
    reason: validationOutcome.reason ?? null
  };
}

export function mapAgent(agent: AgentDescriptorResponse): AgentRecord {
  return {
    agentId: agent.agent_id,
    name: agent.name,
    description: agent.description,
    agentFamily: agent.agent_family ?? undefined,
    framework: agent.framework,
    frameworkVersion: agent.framework_version,
    entrypoint: agent.entrypoint,
    defaultModel: agent.default_model,
    tags: agent.tags,
    capabilities: agent.capabilities,
    publishedAt: agent.published_at,
    sourceFingerprint: agent.source_fingerprint ?? undefined,
    executionReference: mapExecutionReference(agent.execution_reference),
    executionProfile: agent.default_runtime_profile,
    latestValidation: mapValidationRunReference(agent.latest_validation),
    validationEvidence: mapValidationEvidence(agent.validation_evidence),
    validationOutcome: mapValidationOutcome(agent.validation_outcome)
  };
}

export function mapDiscoveredAgent(agent: DiscoveredAgentResponse): DiscoveredAgentRecord {
  return {
    agentId: agent.agent_id,
    name: agent.name,
    description: agent.description,
    agentFamily: agent.agent_family ?? undefined,
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
    executionProfile: agent.default_runtime_profile,
    latestValidation: mapValidationRunReference(agent.latest_validation),
    validationEvidence: mapValidationEvidence(agent.validation_evidence),
    validationOutcome: mapValidationOutcome(agent.validation_outcome)
  };
}
