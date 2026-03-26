import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { exportArtifact, listArtifacts } from "./api";
import type { ExportArtifactInput } from "./model";

const artifactsQueryRoot = ["artifacts"] as const;

export function artifactsQueryOptions() {
  return {
    queryKey: artifactsQueryRoot,
    queryFn: listArtifacts
  };
}

export function useArtifactsQuery() {
  return useQuery(artifactsQueryOptions());
}

export function useExportArtifactMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ExportArtifactInput) => exportArtifact(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: artifactsQueryRoot });
    }
  });
}
