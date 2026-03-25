import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createRun, getRun, listRuns } from "./api";
import type { CreateRunInput, RunListFilters } from "./model";

const runsQueryRoot = ["runs"] as const;

type NormalizedRunFilters = {
  status: RunListFilters["status"] | null;
  project: string | null;
  dataset: string | null;
  model: string | null;
  tag: string | null;
  createdFrom: string | null;
  createdTo: string | null;
};

function normalizeRunFilters(filters: RunListFilters = {}): NormalizedRunFilters {
  return {
    status: filters.status ?? null,
    project: filters.project ?? null,
    dataset: filters.dataset ?? null,
    model: filters.model ?? null,
    tag: filters.tag ?? null,
    createdFrom: filters.createdFrom ?? null,
    createdTo: filters.createdTo ?? null
  };
}

export function runsQueryOptions(filters: RunListFilters = {}) {
  return {
    queryKey: [...runsQueryRoot, normalizeRunFilters(filters)] as const,
    queryFn: () => listRuns(filters)
  };
}

export function runQueryOptions(runId: string) {
  return {
    queryKey: [...runsQueryRoot, "detail", runId] as const,
    queryFn: () => getRun(runId),
    staleTime: 0
  };
}

export function useRunsQuery(filters: RunListFilters = {}) {
  return useQuery(runsQueryOptions(filters));
}

export function useCreateRunMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateRunInput) => createRun(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: runsQueryRoot });
    }
  });
}
