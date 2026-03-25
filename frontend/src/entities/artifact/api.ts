import { request } from "@/src/shared/api/http";
import { mapArtifact, type ApiArtifact } from "./mapper";
import type { ExportArtifactInput } from "./model";

export async function exportArtifact(payload: ExportArtifactInput) {
  return mapArtifact(
    await request<ApiArtifact>("/api/v1/artifacts/export", {
      method: "POST",
      body: JSON.stringify({
        run_ids: payload.runIds,
        format: payload.format ?? "jsonl"
      })
    })
  );
}
