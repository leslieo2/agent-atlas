import { useQuery } from "@tanstack/react-query";
import { getTrajectory } from "./api";

const trajectoriesQueryRoot = ["trajectories"] as const;

export function trajectoryQueryOptions(runId: string) {
  return {
    queryKey: [...trajectoriesQueryRoot, runId] as const,
    queryFn: () => getTrajectory(runId)
  };
}

export function useTrajectoryQuery(runId: string) {
  return useQuery({
    ...trajectoryQueryOptions(runId),
    enabled: Boolean(runId)
  });
}
