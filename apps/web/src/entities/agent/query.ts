import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  bootstrapClaudeCodeAgent,
  listDiscoveredAgents,
  listPublishedAgents,
  publishAgent,
  startValidationRun,
  unpublishAgent
} from "./api";
import { hasActiveAgentValidationLifecycle } from "./lifecycle";

export const discoveredAgentsQueryRoot = ["agents", "discovered"] as const;
export const publishedAgentsQueryRoot = ["agents", "published"] as const;

export function discoveredAgentsQueryOptions() {
  return {
    queryKey: discoveredAgentsQueryRoot,
    queryFn: listDiscoveredAgents,
    refetchInterval: (query: { state: { data?: Awaited<ReturnType<typeof listDiscoveredAgents>> } }) =>
      query.state.data?.some(hasActiveAgentValidationLifecycle) ? 2000 : false
  };
}

export function publishedAgentsQueryOptions() {
  return {
    queryKey: publishedAgentsQueryRoot,
    queryFn: listPublishedAgents,
    refetchInterval: (query: { state: { data?: Awaited<ReturnType<typeof listPublishedAgents>> } }) =>
      query.state.data?.some(hasActiveAgentValidationLifecycle) ? 2000 : false
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

export function useBootstrapClaudeCodeAgentMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => bootstrapClaudeCodeAgent(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: discoveredAgentsQueryRoot });
      void queryClient.invalidateQueries({ queryKey: publishedAgentsQueryRoot });
    }
  });
}

export function useStartValidationRunMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ agentId, payload }: { agentId: string; payload: Parameters<typeof startValidationRun>[1] }) =>
      startValidationRun(agentId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: discoveredAgentsQueryRoot });
      void queryClient.invalidateQueries({ queryKey: publishedAgentsQueryRoot });
    }
  });
}
