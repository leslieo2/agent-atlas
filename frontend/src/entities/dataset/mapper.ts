import type { DatasetResponse as ApiDataset } from "@/src/shared/api/contract";
import type { Dataset } from "./model";

export function mapDataset(dataset: ApiDataset): Dataset {
  return {
    name: dataset.name,
    description: dataset.description ?? null,
    source: dataset.source ?? null,
    version: dataset.version ?? null,
    createdAt: dataset.created_at,
    rows: dataset.rows.map((row) => ({
      sampleId: row.sample_id,
      input: row.input,
      expected: row.expected ?? null,
      tags: row.tags ?? [],
      slice: row.slice ?? null,
      source: row.source ?? null,
      metadata: row.metadata ?? null,
      exportEligible: row.export_eligible ?? null
    }))
  };
}
