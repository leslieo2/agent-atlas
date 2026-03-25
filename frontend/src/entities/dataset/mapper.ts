import type { Dataset } from "./model";

type ApiDataset = {
  name: string;
  rows: Array<{ sample_id: string; input: string }>;
};

export function mapDataset(dataset: ApiDataset): Dataset {
  return {
    name: dataset.name,
    rows: dataset.rows.map((row) => ({ sampleId: row.sample_id, input: row.input }))
  };
}

export type { ApiDataset };

