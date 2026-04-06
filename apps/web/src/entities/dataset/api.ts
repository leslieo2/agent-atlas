import { request } from "@/src/shared/api/http";
import type { DatasetCreate, DatasetResponse, DatasetVersionCreate, DatasetVersionResponse } from "@/src/shared/api/contract";
import { mapDataset } from "./mapper";
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
    rows: payload.rows.map((row) => ({
      sample_id: row.sampleId,
      input: row.input,
      expected: row.expected ?? null,
      tags: row.tags ?? [],
      slice: row.slice ?? null,
      source: row.source ?? null,
      metadata: row.metadata ?? null,
      export_eligible: row.exportEligible ?? null
    }))
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
    rows: payload.rows.map((row) => ({
      sample_id: row.sampleId,
      input: row.input,
      expected: row.expected ?? null,
      tags: row.tags ?? [],
      slice: row.slice ?? null,
      source: row.source ?? null,
      metadata: row.metadata ?? null,
      export_eligible: row.exportEligible ?? null
    }))
  };

  const version = await request<DatasetVersionResponse>(`/api/v1/datasets/${datasetName}/versions`, {
    method: "POST",
    body: JSON.stringify(body)
  });

  return {
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
  };
}

export async function ensureClaudeCodeStarterDataset() {
  return mapDataset(
    await request<DatasetResponse>("/api/v1/datasets/starters/claude-code", {
      method: "POST"
    })
  );
}
