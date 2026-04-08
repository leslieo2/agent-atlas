import type { CompareOutcome, CurationStatus, SampleJudgement } from "@/src/shared/api/contract";
import type { ExperimentCompareSampleRecord, ExperimentRunRecord } from "./model";

export type CompareOutcomeFilter = CompareOutcome | "";

export const COMPARE_OUTCOME_OPTIONS: CompareOutcome[] = [
  "improved",
  "regressed",
  "unchanged_pass",
  "unchanged_fail",
  "candidate_only",
  "baseline_only"
];

export function compareTone(outcome: CompareOutcome) {
  if (outcome === "improved" || outcome === "unchanged_pass") {
    return "success";
  }
  if (outcome === "regressed" || outcome === "baseline_only") {
    return "error";
  }
  return "warn";
}

export function buildCompareLookup(compareSamples: ExperimentCompareSampleRecord[]) {
  return new Map(compareSamples.map((sample) => [sample.datasetSampleId, sample.compareOutcome] as const));
}

export function resolveRunCompareOutcome(
  run: ExperimentRunRecord,
  compareLookup: Map<string, CompareOutcome>
): CompareOutcome | null {
  return compareLookup.get(run.datasetSampleId) ?? run.compareOutcome ?? null;
}

export function matchesExperimentRunFilters({
  run,
  judgementFilter,
  errorCodeFilter,
  sliceFilter,
  tagFilter,
  curationFilter,
  compareLookup,
  compareOutcomeFilter
}: {
  run: ExperimentRunRecord;
  judgementFilter: SampleJudgement | "";
  errorCodeFilter: string;
  sliceFilter: string;
  tagFilter: string;
  curationFilter: CurationStatus | "";
  compareLookup: Map<string, CompareOutcome>;
  compareOutcomeFilter: CompareOutcomeFilter;
}) {
  return matchesRunPreviewFilters({
    run,
    compareOutcome: resolveRunCompareOutcome(run, compareLookup),
    judgementFilter,
    errorCodeFilter,
    sliceFilter,
    tagFilter,
    compareOutcomeFilter,
    curationFilter,
    exportEligibleOnly: false
  });
}

export function matchesRunPreviewFilters({
  run,
  compareOutcome,
  judgementFilter,
  errorCodeFilter,
  sliceFilter,
  tagFilter,
  compareOutcomeFilter,
  curationFilter,
  exportEligibleOnly
}: {
  run: ExperimentRunRecord;
  compareOutcome?: CompareOutcome | null;
  judgementFilter: SampleJudgement | "";
  errorCodeFilter: string;
  sliceFilter: string;
  tagFilter: string;
  compareOutcomeFilter: CompareOutcomeFilter;
  curationFilter: CurationStatus | "";
  exportEligibleOnly: boolean;
}) {
  if (judgementFilter && run.judgement !== judgementFilter) {
    return false;
  }
  if (errorCodeFilter && run.errorCode !== errorCodeFilter) {
    return false;
  }
  if (sliceFilter && run.slice !== sliceFilter) {
    return false;
  }
  if (tagFilter && !run.tags.includes(tagFilter)) {
    return false;
  }
  if (compareOutcomeFilter && compareOutcome !== compareOutcomeFilter) {
    return false;
  }
  if (curationFilter && run.curationStatus !== curationFilter) {
    return false;
  }
  if (exportEligibleOnly && run.exportEligible === false) {
    return false;
  }
  return true;
}
