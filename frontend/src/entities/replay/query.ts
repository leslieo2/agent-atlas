import { useMutation } from "@tanstack/react-query";
import { createReplay } from "./api";
import type { CreateReplayInput } from "./model";

export function useCreateReplayMutation() {
  return useMutation({
    mutationFn: (payload: CreateReplayInput) => createReplay(payload)
  });
}
