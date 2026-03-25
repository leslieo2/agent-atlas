import { request } from "@/src/shared/api/http";
import type { ArtifactExportRequest, ArtifactMetadataResponse } from "@/src/shared/api/contract";
import { mapArtifact } from "./mapper";
import type { ExportArtifactInput } from "./model";

export async function exportArtifact(payload: ExportArtifactInput) {
  const body: ArtifactExportRequest = {
    run_ids: payload.runIds,
    format: payload.format ?? "jsonl"
  };

  return mapArtifact(
    await request<ArtifactMetadataResponse>("/api/v1/artifacts/export", {
      method: "POST",
      body: JSON.stringify(body)
    })
  );
}
