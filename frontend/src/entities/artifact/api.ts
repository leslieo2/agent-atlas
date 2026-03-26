import { request } from "@/src/shared/api/http";
import type { ArtifactExportRequest, ArtifactMetadataResponse } from "@/src/shared/api/contract";
import { mapArtifact } from "./mapper";
import type { ExportArtifactInput } from "./model";

export async function listArtifacts() {
  return (await request<ArtifactMetadataResponse[]>("/api/v1/artifacts")).map(mapArtifact);
}

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

export function getArtifactDownloadUrl(artifactId: string) {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
  return `${apiBase}/api/v1/artifacts/${artifactId}`;
}
