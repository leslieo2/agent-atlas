import { request } from "@/src/shared/api/http";
import type { DatasetCreate, DatasetResponse, DatasetVersionCreate, DatasetVersionResponse } from "@/src/shared/api/contract";
import { mapDataset, mapDatasetVersion, serializeDatasetRow } from "./mapper";
import type { CreateDatasetInput, CreateDatasetVersionInput, DatasetVersionRecord } from "./model";

export async function listDatasets() {
  return (await request<DatasetResponse[]>("/api/v1/datasets")).map(mapDataset);
}

export async function createDataset(payload: CreateDatasetInput) {
  const body: DatasetCreate = {
    name: payload.name,
    description: payload.description ?? null,
    source: payload.source ?? null,
    version: payload.version ?? null,
    rows: payload.rows.map(serializeDatasetRow)
  };

  return mapDataset(
    await request<DatasetResponse>("/api/v1/datasets", {
      method: "POST",
      body: JSON.stringify(body)
    })
  );
}

export async function createDatasetVersion(datasetName: string, payload: CreateDatasetVersionInput): Promise<DatasetVersionRecord> {
  const body: DatasetVersionCreate = {
    version: payload.version ?? null,
    rows: payload.rows.map(serializeDatasetRow)
  };

  const version = await request<DatasetVersionResponse>(`/api/v1/datasets/${datasetName}/versions`, {
    method: "POST",
    body: JSON.stringify(body)
  });

  return mapDatasetVersion(version);
}

export async function ensureClaudeCodeStarterDataset() {
  return mapDataset(
    await request<DatasetResponse>("/api/v1/datasets/starters/claude-code", {
      method: "POST"
    })
  );
}
