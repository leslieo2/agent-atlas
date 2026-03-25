import { useMutation } from "@tanstack/react-query";
import { createEvalJob } from "./api";
import type { CreateEvalJobInput } from "./model";

export function useCreateEvalJobMutation() {
  return useMutation({
    mutationFn: (payload: CreateEvalJobInput) => createEvalJob(payload)
  });
}
