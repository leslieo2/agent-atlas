"use client";

import type { Dataset, DatasetRow } from "@/src/entities/dataset/model";

export function normalizeDatasetName(value: string) {
  return value.trim();
}

export function inferDatasetName(currentName: string, fileName: string) {
  const normalized = normalizeDatasetName(currentName);
  if (normalized) {
    return normalized;
  }

  return fileName.replace(/\.jsonl$/i, "").trim();
}

export function collectUnique(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value)))).sort();
}

export function matchesDatasetRowFilters({
  row,
  sliceFilter,
  tagFilter,
  sourceFilter
}: {
  row: DatasetRow;
  sliceFilter: string;
  tagFilter: string;
  sourceFilter: string;
}) {
  if (sliceFilter && row.slice !== sliceFilter) {
    return false;
  }
  if (tagFilter && !row.tags?.includes(tagFilter)) {
    return false;
  }
  if (sourceFilter && row.source !== sourceFilter) {
    return false;
  }
  return true;
}

export function datasetSummary(dataset: Dataset | null) {
  if (!dataset) {
    return "Waiting for dataset import";
  }

  const parts = [
    `${dataset.rows.length} samples`,
    dataset.source ? `source ${dataset.source}` : null,
    dataset.version ? `version ${dataset.version}` : null
  ].filter(Boolean);

  return parts.join(" · ");
}

export function datasetVersionLabel(version: string | null | undefined) {
  return version ? `Version ${version}` : "Unversioned";
}
