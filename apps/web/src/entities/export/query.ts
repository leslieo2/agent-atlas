import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createExport, listExports } from "./api";
import type { CreateExportInput } from "./model";

export const exportsQueryRoot = ["exports"] as const;

export function exportsQueryOptions() {
  return {
    queryKey: exportsQueryRoot,
    queryFn: listExports
  };
}

export function useExportsQuery() {
  return useQuery(exportsQueryOptions());
}

export function useCreateExportMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateExportInput) => createExport(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: exportsQueryRoot });
    }
  });
}
