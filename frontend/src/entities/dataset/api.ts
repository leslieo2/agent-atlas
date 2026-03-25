import { request } from "@/src/shared/api/http";
import type { DatasetCreate, DatasetResponse } from "@/src/shared/api/contract";
import { mapDataset } from "./mapper";
import type { CreateDatasetInput } from "./model";

export async function listDatasets() {
  return (await request<DatasetResponse[]>("/api/v1/datasets")).map(mapDataset);
}

export async function createDataset(payload: CreateDatasetInput) {
  const body: DatasetCreate = {
    name: payload.name,
    rows: payload.rows.map((row) => ({
      sample_id: row.sampleId,
      input: row.input,
      expected: row.expected ?? null,
      tags: row.tags ?? []
    }))
  };

  return mapDataset(
    await request<DatasetResponse>("/api/v1/datasets", {
      method: "POST",
      body: JSON.stringify(body)
    })
  );
}
