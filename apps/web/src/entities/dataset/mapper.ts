import type { DatasetResponse as ApiDataset } from "@/src/shared/api/contract";
import type { Dataset } from "./model";

export function mapDataset(dataset: ApiDataset): Dataset {
  const versions = dataset.versions.map((version) => ({
    datasetVersionId: version.dataset_version_id,
    datasetName: version.dataset_name,
    version: version.version ?? null,
    createdAt: version.created_at,
    rowCount: version.row_count,
    rows: version.rows.map((row) => ({
      sampleId: row.sample_id,
      input: row.input,
      expected: row.expected ?? null,
      tags: row.tags ?? [],
      slice: row.slice ?? null,
      source: row.source ?? null,
      metadata: row.metadata ?? null,
      exportEligible: row.export_eligible ?? null
    }))
  }));
  const currentVersion =
    versions.find((version) => version.datasetVersionId === (dataset.current_version_id ?? null)) ??
    versions[versions.length - 1] ??
    null;

  return {
    name: dataset.name,
    description: dataset.description ?? null,
    source: dataset.source ?? null,
    createdAt: dataset.created_at,
    currentVersionId: dataset.current_version_id ?? null,
    version: currentVersion?.version ?? null,
    rows: currentVersion?.rows ?? [],
    versions
  };
}
