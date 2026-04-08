"use client";

import { getAgentValidationLifecycle } from "@/src/entities/agent/lifecycle";
import type { AgentRecord } from "@/src/entities/agent/model";
import type { ExperimentRecord, ExperimentRunRecord } from "@/src/entities/experiment/model";
import type { CompareOutcome, CurationStatus, RunStatus, SampleJudgement } from "@/src/shared/api/contract";

export type ExperimentAgentOption = Pick<AgentRecord, "agentId" | "name" | "defaultModel" | "executionProfile">;

export function canSelectPublishedAgentForExperiment(agent: AgentRecord) {
  const validationLifecycle = getAgentValidationLifecycle(agent);
  return validationLifecycle.isSuccessful;
}

export function parseTags(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function experimentTone(status: string) {
  if (status === "completed") {
    return "success";
  }
  if (status === "failed" || status === "cancelled") {
    return "error";
  }
  return "warn";
}

export function judgementTone(judgement?: SampleJudgement | null) {
  if (judgement === "passed") {
    return "success";
  }
  if (judgement === "failed" || judgement === "runtime_error") {
    return "error";
  }
  return "warn";
}

const CURATION_READY_RUN_STATUSES = new Set<RunStatus>(["succeeded", "failed", "cancelled", "lost"]);

export function canCurateRun(run: ExperimentRunRecord) {
  return CURATION_READY_RUN_STATUSES.has(run.runStatus);
}

export function curationDisabledReason(run: ExperimentRunRecord, isMutationPending: boolean) {
  if (isMutationPending) {
    return "Updating curation state...";
  }
  if (!canCurateRun(run)) {
    return "Wait for this sample to finish before changing curation.";
  }
  return undefined;
}

export function uniqueStrings(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value)))).sort();
}

export function experimentLabel(record: ExperimentRecord) {
  return `${record.name} · ${record.publishedAgentId}`;
}

export function experimentNextStep(record: ExperimentRecord | null) {
  if (!record) {
    return "Create an experiment from a governed asset to start collecting evidence.";
  }
  if (record.status === "completed") {
    return "Review the evidence summary, compare against a baseline if needed, then curate runs for export.";
  }
  if (record.status === "failed" || record.status === "cancelled") {
    return "Inspect the current evidence summary before deciding whether to retry or compare.";
  }
  return "Let the run finish, then move into compare and curation once evidence is available.";
}

export function datasetVersionOptionLabel(datasetName: string, version: string | null | undefined) {
  return `${datasetName} · ${version ? `Version ${version}` : "Unversioned"}`;
}

export function exportsHandoffHref(selectedExperiment: ExperimentRecord | null, baselineExperimentId: string) {
  if (!selectedExperiment) {
    return "/exports";
  }

  const params = new URLSearchParams();
  if (baselineExperimentId) {
    params.set("candidate", selectedExperiment.experimentId);
    params.set("baseline", baselineExperimentId);
  } else {
    params.set("experiment", selectedExperiment.experimentId);
  }
  return `/exports?${params.toString()}`;
}

export type PatchRunPayload = {
  curationStatus?: CurationStatus;
  exportEligible?: boolean;
};

export type CompareFilterValue = CompareOutcome | "";
