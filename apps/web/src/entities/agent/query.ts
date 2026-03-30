import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listDiscoveredAgents, listPublishedAgents, publishAgent, unpublishAgent } from "./api";

export const discoveredAgentsQueryRoot = ["agents", "discovered"] as const;
export const publishedAgentsQueryRoot = ["agents", "published"] as const;

export function discoveredAgentsQueryOptions() {
  return {
    queryKey: discoveredAgentsQueryRoot,
    queryFn: listDiscoveredAgents
  };
}

export function publishedAgentsQueryOptions() {
  return {
    queryKey: publishedAgentsQueryRoot,
    queryFn: listPublishedAgents
  };
}

export function useDiscoveredAgentsQuery() {
  return useQuery(discoveredAgentsQueryOptions());
}

export function usePublishedAgentsQuery() {
  return useQuery(publishedAgentsQueryOptions());
}

export function usePublishAgentMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (agentId: string) => publishAgent(agentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: discoveredAgentsQueryRoot });
      void queryClient.invalidateQueries({ queryKey: publishedAgentsQueryRoot });
    }
  });
}

export function useUnpublishAgentMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (agentId: string) => unpublishAgent(agentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: discoveredAgentsQueryRoot });
      void queryClient.invalidateQueries({ queryKey: publishedAgentsQueryRoot });
    }
  });
}
