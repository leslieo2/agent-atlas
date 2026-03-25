import { useMutation } from "@tanstack/react-query";
import { createEvalJob, getEvalJob } from "./api";
import type { CreateEvalJobInput } from "./model";

const evalJobsQueryRoot = ["eval-jobs"] as const;

export function evalJobQueryOptions(jobId: string) {
  return {
    queryKey: [...evalJobsQueryRoot, jobId] as const,
    queryFn: () => getEvalJob(jobId),
    staleTime: 0
  };
}

export function useCreateEvalJobMutation() {
  return useMutation({
    mutationFn: (payload: CreateEvalJobInput) => createEvalJob(payload)
  });
}
