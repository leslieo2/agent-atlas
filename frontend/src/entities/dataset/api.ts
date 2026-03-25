import { request } from "@/src/shared/api/http";
import { mapDataset, type ApiDataset } from "./mapper";
import type { CreateDatasetInput } from "./model";

export async function listDatasets() {
  return (await request<ApiDataset[]>("/api/v1/datasets")).map(mapDataset);
}

export async function createDataset(payload: CreateDatasetInput) {
  return mapDataset(
    await request<ApiDataset>("/api/v1/datasets", {
      method: "POST",
      body: JSON.stringify({
        name: payload.name,
        rows: payload.rows.map((row) => ({
          sample_id: row.sampleId,
          input: row.input,
          expected: row.expected ?? null,
          tags: row.tags ?? []
        }))
      })
    })
  );
}

