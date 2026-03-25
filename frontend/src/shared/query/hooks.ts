import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { exportArtifact } from "@/src/entities/artifact/api";
import type { ExportArtifactInput } from "@/src/entities/artifact/model";
import { createDataset, listDatasets } from "@/src/entities/dataset/api";
import type { CreateDatasetInput } from "@/src/entities/dataset/model";
import { createEvalJob } from "@/src/entities/eval/api";
import type { CreateEvalJobInput } from "@/src/entities/eval/model";
import { createReplay } from "@/src/entities/replay/api";
import type { CreateReplayInput } from "@/src/entities/replay/model";
import { createRun, listRuns } from "@/src/entities/run/api";
import type { CreateRunInput, RunListFilters } from "@/src/entities/run/model";
import { getTrajectory } from "@/src/entities/trajectory/api";

const queryRoots = {
  runs: ["runs"] as const,
  trajectories: ["trajectories"] as const,
  datasets: ["datasets"] as const
};

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
    queryKey: [...queryRoots.runs, normalizeRunFilters(filters)] as const,
    queryFn: () => listRuns(filters)
  };
}

export function trajectoryQueryOptions(runId: string) {
  return {
    queryKey: [...queryRoots.trajectories, runId] as const,
    queryFn: () => getTrajectory(runId)
  };
}

export function datasetsQueryOptions() {
  return {
    queryKey: queryRoots.datasets,
    queryFn: listDatasets
  };
}

export function useRunsQuery(filters: RunListFilters = {}) {
  return useQuery(runsQueryOptions(filters));
}

export function useTrajectoryQuery(runId: string) {
  return useQuery({
    ...trajectoryQueryOptions(runId),
    enabled: Boolean(runId)
  });
}

export function useDatasetsQuery() {
  return useQuery(datasetsQueryOptions());
}

export function useCreateRunMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateRunInput) => createRun(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryRoots.runs });
    }
  });
}

export function useCreateReplayMutation() {
  return useMutation({
    mutationFn: (payload: CreateReplayInput) => createReplay(payload)
  });
}

export function useCreateEvalJobMutation() {
  return useMutation({
    mutationFn: (payload: CreateEvalJobInput) => createEvalJob(payload)
  });
}

export function useCreateDatasetMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateDatasetInput) => createDataset(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryRoots.datasets });
    }
  });
}

export function useExportArtifactMutation() {
  return useMutation({
    mutationFn: (payload: ExportArtifactInput) => exportArtifact(payload)
  });
}
