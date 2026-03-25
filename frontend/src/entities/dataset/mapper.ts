import type { DatasetResponse as ApiDataset } from "@/src/shared/api/contract";
import type { Dataset } from "./model";

export function mapDataset(dataset: ApiDataset): Dataset {
  return {
    name: dataset.name,
    rows: dataset.rows.map((row) => ({ sampleId: row.sample_id, input: row.input }))
  };
}
