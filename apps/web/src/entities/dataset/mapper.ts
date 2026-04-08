import type {
  DatasetResponse as ApiDataset,
  DatasetSample as ApiDatasetRow,
  DatasetVersionResponse as ApiDatasetVersion
} from "@/src/shared/api/contract";
import type { Dataset, DatasetRow, DatasetVersionRecord } from "./model";

export function mapDatasetRow(row: ApiDatasetRow): DatasetRow {
  return {
    sampleId: row.sample_id,
    input: row.input,
    expected: row.expected ?? null,
    tags: row.tags ?? [],
    slice: row.slice ?? null,
    source: row.source ?? null,
    metadata: row.metadata ?? null,
    exportEligible: row.export_eligible ?? null
  };
}

export function serializeDatasetRow(row: DatasetRow): ApiDatasetRow {
  return {
    sample_id: row.sampleId,
    input: row.input,
    expected: row.expected ?? null,
    tags: row.tags ?? [],
    slice: row.slice ?? null,
    source: row.source ?? null,
    metadata: row.metadata ?? null,
    export_eligible: row.exportEligible ?? null
  };
}

export function mapDatasetVersion(version: ApiDatasetVersion): DatasetVersionRecord {
  return {
    datasetVersionId: version.dataset_version_id,
    datasetName: version.dataset_name,
    version: version.version ?? null,
    createdAt: version.created_at,
    rowCount: version.row_count,
    rows: version.rows.map(mapDatasetRow)
  };
}

export function mapDataset(dataset: ApiDataset): Dataset {
  const versions = dataset.versions.map(mapDatasetVersion);
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
