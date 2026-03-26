import { useQuery } from "@tanstack/react-query";
import { listAgents } from "./api";

const agentsQueryRoot = ["agents"] as const;

export function agentsQueryOptions() {
  return {
    queryKey: agentsQueryRoot,
    queryFn: listAgents
  };
}

export function useAgentsQuery() {
  return useQuery(agentsQueryOptions());
}
