import { useQuery } from "@tanstack/react-query";
import { listRunTraces } from "./api";

const tracesQueryRoot = ["traces"] as const;

export function traceQueryOptions(runId: string) {
  return {
    queryKey: [...tracesQueryRoot, runId] as const,
    queryFn: () => listRunTraces(runId),
    staleTime: 0
  };
}

export function useRunTracesQuery(runId: string) {
  return useQuery({
    ...traceQueryOptions(runId),
    enabled: Boolean(runId)
  });
}
