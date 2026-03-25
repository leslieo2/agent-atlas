import { useMutation } from "@tanstack/react-query";
import { exportArtifact } from "./api";
import type { ExportArtifactInput } from "./model";

export function useExportArtifactMutation() {
  return useMutation({
    mutationFn: (payload: ExportArtifactInput) => exportArtifact(payload)
  });
}
