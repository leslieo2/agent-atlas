import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createEvalJob, listEvalJobs, listEvalSamples } from "./api";
import { runsQueryRoot } from "@/src/entities/run/query";
import type { CreateEvalJobInput } from "./model";

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

export function useEvalJobsQuery() {
  return useQuery(evalJobsQueryOptions());
}

export function useEvalSamplesQuery(evalJobId: string) {
  return useQuery(evalSamplesQueryOptions(evalJobId));
}

export function useCreateEvalJobMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateEvalJobInput) => createEvalJob(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: evalJobsQueryRoot });
      void queryClient.invalidateQueries({ queryKey: runsQueryRoot });
    }
  });
}
