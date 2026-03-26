import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listAgents, listDiscoveredAgents, publishAgent, unpublishAgent } from "./api";

export const agentsQueryRoot = ["agents"] as const;
export const discoveredAgentsQueryRoot = ["agents", "discovered"] as const;

export function agentsQueryOptions() {
  return {
    queryKey: agentsQueryRoot,
    queryFn: listAgents
  };
}

export function discoveredAgentsQueryOptions() {
  return {
    queryKey: discoveredAgentsQueryRoot,
    queryFn: listDiscoveredAgents
  };
}

export function useAgentsQuery() {
  return useQuery(agentsQueryOptions());
}

export function useDiscoveredAgentsQuery() {
  return useQuery(discoveredAgentsQueryOptions());
}

export function usePublishAgentMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (agentId: string) => publishAgent(agentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: agentsQueryRoot });
      void queryClient.invalidateQueries({ queryKey: discoveredAgentsQueryRoot });
    }
  });
}

export function useUnpublishAgentMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (agentId: string) => unpublishAgent(agentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: agentsQueryRoot });
      void queryClient.invalidateQueries({ queryKey: discoveredAgentsQueryRoot });
    }
  });
}
