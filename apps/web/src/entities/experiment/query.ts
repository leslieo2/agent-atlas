import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  cancelExperiment,
  compareExperiments,
  createExperiment,
  listExperimentRuns,
  listExperiments,
  patchExperimentRun,
  startExperiment
} from "./api";
import type { CreateExperimentInput, ExperimentRunPatchInput } from "./model";

export const experimentsQueryRoot = ["experiments"] as const;

export function experimentsQueryOptions() {
  return {
    queryKey: experimentsQueryRoot,
    queryFn: listExperiments
  };
}

export function experimentRunsQueryOptions(experimentId: string) {
  return {
    queryKey: [...experimentsQueryRoot, experimentId, "runs"] as const,
    queryFn: () => listExperimentRuns(experimentId),
    enabled: Boolean(experimentId)
  };
}

export function experimentCompareQueryOptions(baselineExperimentId: string, candidateExperimentId: string) {
  return {
    queryKey: [...experimentsQueryRoot, "compare", baselineExperimentId, candidateExperimentId] as const,
    queryFn: () => compareExperiments(baselineExperimentId, candidateExperimentId),
    enabled: Boolean(baselineExperimentId && candidateExperimentId)
  };
}

export function useExperimentsQuery() {
  return useQuery(experimentsQueryOptions());
}

export function useExperimentRunsQuery(experimentId: string) {
  return useQuery(experimentRunsQueryOptions(experimentId));
}

export function useExperimentCompareQuery(baselineExperimentId: string, candidateExperimentId: string) {
  return useQuery(experimentCompareQueryOptions(baselineExperimentId, candidateExperimentId));
}

export function useCreateExperimentMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateExperimentInput) => createExperiment(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: experimentsQueryRoot });
    }
  });
}

export function useStartExperimentMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (experimentId: string) => startExperiment(experimentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: experimentsQueryRoot });
    }
  });
}

export function useCancelExperimentMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (experimentId: string) => cancelExperiment(experimentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: experimentsQueryRoot });
    }
  });
}

export function usePatchExperimentRunMutation(experimentId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ runId, payload }: { runId: string; payload: ExperimentRunPatchInput }) =>
      patchExperimentRun(experimentId, runId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [...experimentsQueryRoot, experimentId, "runs"] });
      void queryClient.invalidateQueries({ queryKey: [...experimentsQueryRoot, "compare"] });
      void queryClient.invalidateQueries({ queryKey: ["exports"] });
    }
  });
}
