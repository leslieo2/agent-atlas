"use client";

export function uniqueStrings(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value)))).sort();
}

export function formatTimestamp(value: string) {
  return new Date(value).toLocaleString("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

export function formatBytes(value: number) {
  if (!Number.isFinite(value) || value <= 0) {
    return "0 B";
  }

  if (value < 1024) {
    return `${value} B`;
  }

  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }

  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export function buildActiveFilters(filters: {
  judgementFilter: string;
  errorCodeFilter: string;
  sliceFilter: string;
  tagFilter: string;
  compareOutcomeFilter: string;
  curationFilter: string;
  exportEligibleOnly: boolean;
}) {
  return [
    filters.judgementFilter ? `Judgement: ${filters.judgementFilter}` : null,
    filters.errorCodeFilter ? `Error: ${filters.errorCodeFilter}` : null,
    filters.sliceFilter ? `Slice: ${filters.sliceFilter}` : null,
    filters.tagFilter ? `Tag: ${filters.tagFilter}` : null,
    filters.compareOutcomeFilter ? `Compare: ${filters.compareOutcomeFilter}` : null,
    filters.curationFilter ? `Curation: ${filters.curationFilter}` : null,
    filters.exportEligibleOnly ? null : "Eligibility: include ineligible rows"
  ].filter((value): value is string => Boolean(value));
}

function formatFilterSummaryValue(value: unknown) {
  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "none";
  }
  if (typeof value === "boolean") {
    return value ? "yes" : "no";
  }
  if (value == null || value === "") {
    return "none";
  }
  return String(value);
}

export function summarizeFilterSummary(filtersSummary: Record<string, unknown>) {
  const entries = Object.entries(filtersSummary);
  if (!entries.length) {
    return ["Default export rules"];
  }

  return entries.map(([key, value]) => `${key}: ${formatFilterSummaryValue(value)}`);
}
