"use client";

import { getAgentValidationLifecycle } from "@/src/entities/agent/lifecycle";
import type {
  AgentRecord,
  AgentValidationEvidenceSummaryRecord,
  AgentValidationOutcomeSummaryRecord,
  AgentValidationRunReferenceRecord,
  ExecutionReferenceRecord
} from "@/src/entities/agent/model";
import { executionProfileSummary } from "@/src/shared/runtime/identity";

export type AgentGroup = {
  title: string;
  description: string;
  items: AgentRecord[];
};

export type AgentReadiness = "ready" | "validating" | "needs_validation" | "needs_review";

export type EntryFocus = {
  agentId: string;
  name: string;
};

export const CLAUDE_CODE_BRIDGE_AGENT_ID = "claude-code-starter";

export function fallbackValidationTimestamp(agent: AgentRecord) {
  return (
    agent.latestValidation?.completedAt ??
    agent.latestValidation?.startedAt ??
    agent.latestValidation?.createdAt ??
    agent.publishedAt ??
    new Date(0).toISOString()
  );
}

export function getAgentReadiness(agent: AgentRecord): AgentReadiness {
  const validationLifecycle = getAgentValidationLifecycle(agent);
  if (validationLifecycle.isActive) {
    return "validating";
  }
  if (validationLifecycle.isSuccessful) {
    return "ready";
  }
  if (validationLifecycle.isBlocking) {
    return "needs_review";
  }
  return "needs_validation";
}

export function readinessLabel(state: AgentReadiness) {
  if (state === "validating") {
    return "Validating";
  }
  if (state === "needs_validation") {
    return "Needs validation";
  }
  if (state === "needs_review") {
    return "Needs review";
  }
  return "Ready";
}

export function validationTone(agent: AgentRecord) {
  return getAgentValidationLifecycle(agent).tone;
}

export function validationRunTone(status?: string | null) {
  return getAgentValidationLifecycle({
    latestValidation: status ? ({ status } as AgentValidationRunReferenceRecord) : null,
    validationOutcome: null
  }).tone;
}

export function executionReferenceSummary(executionReference?: ExecutionReferenceRecord | null) {
  if (!executionReference) {
    return "-";
  }
  if (executionReference.imageRef) {
    return executionReference.imageRef;
  }
  if (executionReference.artifactRef) {
    return executionReference.artifactRef;
  }
  return "-";
}

export function shortSourceFingerprint(sourceFingerprint?: string) {
  const fingerprint = sourceFingerprint?.trim() ?? "";
  if (!fingerprint) {
    return "-";
  }
  return fingerprint.slice(0, 12);
}

export function defaultRuntimeSummary(agent: AgentRecord) {
  return executionProfileSummary(agent.executionProfile);
}

export function formatValidationTimestamp(validationRun?: AgentValidationRunReferenceRecord | null) {
  const value = validationRun?.completedAt ?? validationRun?.startedAt ?? validationRun?.createdAt ?? null;
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString("en");
}

export function validationSummaryStatus(
  validationRun?: AgentValidationRunReferenceRecord | null,
  validationOutcome?: AgentValidationOutcomeSummaryRecord | null
) {
  return validationRun?.status ?? validationOutcome?.status ?? "unknown";
}

export function validationEvidenceLabel(validationEvidence?: AgentValidationEvidenceSummaryRecord | null) {
  if (!validationEvidence) {
    return "-";
  }
  if (validationEvidence.artifactRef) {
    return validationEvidence.artifactRef;
  }
  if (validationEvidence.imageRef) {
    return validationEvidence.imageRef;
  }
  return "-";
}

export function nextStepLabel(agent: AgentRecord) {
  const readiness = getAgentReadiness(agent);
  if (readiness === "validating") {
    return "Atlas is still running the latest validation. Wait for the active run to finish before handing this asset into experiments.";
  }
  if (readiness === "needs_validation") {
    return "Run validation on this governed asset before Atlas treats it as experiment-ready.";
  }
  if (readiness === "needs_review") {
    return "Review the latest validation run and evidence before handing this asset into a new experiment.";
  }
  return "Hand this ready asset into the next experiment.";
}

export function entryFocusSummary(agent?: AgentRecord | null) {
  if (!agent) {
    return "Import a runnable asset or add the Claude Code bridge, then validate it here before using the asset in experiments.";
  }
  const readiness = getAgentReadiness(agent);
  if (readiness === "validating") {
    return `${agent.name} has an active validation run. Wait for the latest run to resolve before using this asset in experiments.`;
  }
  if (readiness === "needs_validation") {
    return `${agent.name} still needs a successful validation run before Atlas exposes it as experiment-ready.`;
  }
  if (readiness === "needs_review") {
    return `${agent.name} needs validation review. Resolve the latest outcome before using this asset in experiments.`;
  }
  return `${agent.name} is ready for experiments based on its latest validation summary.`;
}

export function validationPayload(agent: AgentRecord) {
  return {
    project: "atlas-validation",
    dataset: "controlled-validation",
    input_summary: `Validate ${agent.name} from the Agents surface`,
    prompt: "alpha",
    tags: ["agents-surface"],
    project_metadata: {
      validation_target: agent.agentId,
      validation_surface: "agents"
    },
    executor_config: agent.executionProfile
  };
}

export function bridgeAlreadyExistsMessage(agent: AgentRecord) {
  return `${agent.name} already exists as the Claude Code bridge, and the starter code-edit dataset is ready too. Review its validation here before using it in experiments.`;
}
