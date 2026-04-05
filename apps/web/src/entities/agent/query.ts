import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createClaudeCodeBridgeAsset,
  importAgent,
  listPublishedAgents,
  startValidationRun
} from "./api";
import { hasActiveAgentValidationLifecycle } from "./lifecycle";

export const publishedAgentsQueryRoot = ["agents", "published"] as const;

export function publishedAgentsQueryOptions() {
  return {
    queryKey: publishedAgentsQueryRoot,
    queryFn: listPublishedAgents,
    refetchInterval: (query: { state: { data?: Awaited<ReturnType<typeof listPublishedAgents>> } }) =>
      query.state.data?.some(hasActiveAgentValidationLifecycle) ? 2000 : false
  };
}

export function usePublishedAgentsQuery() {
  return useQuery(publishedAgentsQueryOptions());
}

export function useCreateClaudeCodeBridgeAssetMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => createClaudeCodeBridgeAsset(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: publishedAgentsQueryRoot });
    }
  });
}

export function useImportAgentMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: importAgent,
    onSuccess: () => {
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
      void queryClient.invalidateQueries({ queryKey: publishedAgentsQueryRoot });
    }
  });
}
