import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { compareEvalJobs, createEvalJob, listEvalJobs, listEvalSamples, patchEvalSample } from "./api";
import type { CreateEvalJobInput, EvalSamplePatchInput } from "./model";

export const evalJobsQueryRoot = ["eval-jobs"] as const;

export function evalJobsQueryOptions() {
  return {
    queryKey: evalJobsQueryRoot,
    queryFn: listEvalJobs
  };
}

export function evalSamplesQueryOptions(evalJobId: string) {
  return {
    queryKey: [...evalJobsQueryRoot, evalJobId, "samples"] as const,
    queryFn: () => listEvalSamples(evalJobId),
    enabled: Boolean(evalJobId)
  };
}

export function evalCompareQueryOptions(baselineEvalJobId: string, candidateEvalJobId: string) {
  return {
    queryKey: [...evalJobsQueryRoot, "compare", baselineEvalJobId, candidateEvalJobId] as const,
    queryFn: () => compareEvalJobs(baselineEvalJobId, candidateEvalJobId),
    enabled: Boolean(baselineEvalJobId && candidateEvalJobId)
  };
}

export function useEvalJobsQuery() {
  return useQuery(evalJobsQueryOptions());
}

export function useEvalSamplesQuery(evalJobId: string) {
  return useQuery(evalSamplesQueryOptions(evalJobId));
}

export function useEvalCompareQuery(baselineEvalJobId: string, candidateEvalJobId: string) {
  return useQuery(evalCompareQueryOptions(baselineEvalJobId, candidateEvalJobId));
}

export function useCreateEvalJobMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateEvalJobInput) => createEvalJob(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: evalJobsQueryRoot });
    }
  });
}

export function usePatchEvalSampleMutation(evalJobId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ datasetSampleId, payload }: { datasetSampleId: string; payload: EvalSamplePatchInput }) =>
      patchEvalSample(evalJobId, datasetSampleId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [...evalJobsQueryRoot, evalJobId, "samples"] });
      void queryClient.invalidateQueries({ queryKey: [...evalJobsQueryRoot, "compare"] });
      void queryClient.invalidateQueries({ queryKey: ["exports"] });
    }
  });
}
