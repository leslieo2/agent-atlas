import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createDataset, createDatasetVersion, listDatasets } from "./api";
import type { CreateDatasetInput, CreateDatasetVersionInput } from "./model";

const datasetsQueryRoot = ["datasets"] as const;

export function datasetsQueryOptions() {
  return {
    queryKey: datasetsQueryRoot,
    queryFn: listDatasets
  };
}

export function useDatasetsQuery() {
  return useQuery(datasetsQueryOptions());
}

export function useCreateDatasetMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateDatasetInput) => createDataset(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: datasetsQueryRoot });
    }
  });
}

export function useCreateDatasetVersionMutation(datasetName: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateDatasetVersionInput) => createDatasetVersion(datasetName, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: datasetsQueryRoot });
    }
  });
}
