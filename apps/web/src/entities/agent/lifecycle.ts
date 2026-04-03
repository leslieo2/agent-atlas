import type { AgentRecord, AgentValidationOutcomeSummaryRecord, AgentValidationRunReferenceRecord } from "./model";

type AgentValidationSurface = Pick<AgentRecord, "latestValidation" | "validationOutcome"> & {
  validationStatus?: "valid" | "invalid";
};

export type AgentValidationLifecycle = {
  status: string;
  tone: "success" | "warn" | "error";
  isActive: boolean;
  isBlocking: boolean;
  isSuccessful: boolean;
};

const ACTIVE_RUN_STATUSES = new Set(["queued", "starting", "running", "cancelling"]);
const FAILURE_RUN_STATUSES = new Set(["failed", "cancelled", "lost"]);
const SUCCESS_RUN_STATUSES = new Set(["succeeded"]);
const FAILURE_OUTCOME_STATUSES = new Set(["failed", "runtime_error", "invalid"]);
const SUCCESS_OUTCOME_STATUSES = new Set(["passed", "succeeded", "valid"]);

function normalizeStatus(value?: string | null) {
  return value?.trim().toLowerCase() ?? "";
}

function statusFromRun(validationRun?: AgentValidationRunReferenceRecord | null) {
  return normalizeStatus(validationRun?.status);
}

function statusFromOutcome(validationOutcome?: AgentValidationOutcomeSummaryRecord | null) {
  return normalizeStatus(validationOutcome?.status);
}

export function getAgentValidationLifecycle(agent: AgentValidationSurface): AgentValidationLifecycle {
  const runStatus = statusFromRun(agent.latestValidation);
  const outcomeStatus = statusFromOutcome(agent.validationOutcome);

  if (ACTIVE_RUN_STATUSES.has(runStatus) || outcomeStatus === "running") {
    return {
      status: runStatus || outcomeStatus || "running",
      tone: "warn",
      isActive: true,
      isBlocking: true,
      isSuccessful: false
    };
  }

  if (FAILURE_RUN_STATUSES.has(runStatus) || FAILURE_OUTCOME_STATUSES.has(outcomeStatus) || agent.validationStatus === "invalid") {
    return {
      status: runStatus || outcomeStatus || agent.validationStatus || "invalid",
      tone: "error",
      isActive: false,
      isBlocking: true,
      isSuccessful: false
    };
  }

  if (SUCCESS_RUN_STATUSES.has(runStatus) || SUCCESS_OUTCOME_STATUSES.has(outcomeStatus)) {
    return {
      status: runStatus || outcomeStatus,
      tone: "success",
      isActive: false,
      isBlocking: false,
      isSuccessful: true
    };
  }

  return {
    status: agent.validationStatus ?? "unknown",
    tone: "warn",
    isActive: false,
    isBlocking: false,
    isSuccessful: false
  };
}

export function hasActiveAgentValidationLifecycle(agent: AgentValidationSurface) {
  return getAgentValidationLifecycle(agent).isActive;
}
