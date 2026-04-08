"use client";

import { useMemo, useState } from "react";
import {
  useCreateClaudeCodeBridgeAssetMutation,
  useImportAgentMutation,
  usePublishedAgentsQuery,
  useStartValidationRunMutation
} from "@/src/entities/agent/query";
import { useEnsureClaudeCodeStarterDatasetMutation } from "@/src/entities/dataset/query";
import type { AgentRecord, ImportAgentInput } from "@/src/entities/agent/model";
import {
  AgentGroup,
  CLAUDE_CODE_BRIDGE_AGENT_ID,
  EntryFocus,
  bridgeAlreadyExistsMessage,
  getAgentReadiness,
  validationPayload
} from "./model";

export function useAgentControlPlane() {
  const publishedAgentsQuery = usePublishedAgentsQuery();
  const bootstrapMutation = useCreateClaudeCodeBridgeAssetMutation();
  const starterDatasetMutation = useEnsureClaudeCodeStarterDatasetMutation();
  const importMutation = useImportAgentMutation();
  const validationMutation = useStartValidationRunMutation();
  const [actionMessage, setActionMessage] = useState("");
  const [entryFocus, setEntryFocus] = useState<EntryFocus | null>(null);
  const [importForm, setImportForm] = useState<ImportAgentInput>({
    agentId: "",
    name: "",
    description: "",
    framework: "openai-agents-sdk",
    defaultModel: "",
    entrypoint: "",
    tags: []
  });

  const agents = useMemo<AgentRecord[]>(() => publishedAgentsQuery.data ?? [], [publishedAgentsQuery.data]);
  const focusedAgent = useMemo(
    () => agents.find((agent) => agent.agentId === entryFocus?.agentId) ?? null,
    [agents, entryFocus]
  );
  const existingClaudeBridge = useMemo(
    () => agents.find((agent) => agent.agentId === CLAUDE_CODE_BRIDGE_AGENT_ID) ?? null,
    [agents]
  );

  const groups = useMemo<AgentGroup[]>(
    () => [
      {
        title: "Ready",
        description: "Governed assets ready to generate RL evaluation data.",
        items: agents.filter((agent) => getAgentReadiness(agent) === "ready")
      },
      {
        title: "Validating",
        description: "Assets with an active validation run that still owns the current lifecycle state.",
        items: agents.filter((agent) => getAgentReadiness(agent) === "validating")
      },
      {
        title: "Needs validation",
        description: "Governed assets that still need one successful validation run before Atlas exposes them to experiments.",
        items: agents.filter((agent) => getAgentReadiness(agent) === "needs_validation")
      },
      {
        title: "Needs review",
        description: "Assets whose latest validation run ended in a blocking state and need evidence review before handoff.",
        items: agents.filter((agent) => getAgentReadiness(agent) === "needs_review")
      }
    ],
    [agents]
  );

  const errorMessage =
    (importMutation.error instanceof Error && importMutation.error.message) ||
    (bootstrapMutation.error instanceof Error && bootstrapMutation.error.message) ||
    (starterDatasetMutation.error instanceof Error && starterDatasetMutation.error.message) ||
    (validationMutation.error instanceof Error && validationMutation.error.message) ||
    (publishedAgentsQuery.error instanceof Error && publishedAgentsQuery.error.message) ||
    "";

  const isLoading = publishedAgentsQuery.isLoading;
  const validationBacklog = groups[1].items.length + groups[2].items.length + groups[3].items.length;

  async function handleBootstrap() {
    if (existingClaudeBridge) {
      await starterDatasetMutation.mutateAsync();
      bootstrapMutation.reset();
      setEntryFocus({ agentId: existingClaudeBridge.agentId, name: existingClaudeBridge.name });
      setActionMessage(bridgeAlreadyExistsMessage(existingClaudeBridge));
      return;
    }

    try {
      const [agent] = await Promise.all([bootstrapMutation.mutateAsync(), starterDatasetMutation.mutateAsync()]);
      setEntryFocus({ agentId: agent.agentId, name: agent.name });
      setActionMessage(
        `Added ${agent.name} as the Claude Code bridge and prepared the starter code-edit dataset. Review validation here, then use the starter flow in experiments.`
      );
    } catch (error) {
      if (error instanceof Error && error.message.includes("conflicts with an existing governed asset")) {
        const refreshed = await publishedAgentsQuery.refetch();
        const bridge = refreshed.data?.find((agent) => agent.agentId === CLAUDE_CODE_BRIDGE_AGENT_ID) ?? null;
        if (bridge) {
          await starterDatasetMutation.mutateAsync();
          bootstrapMutation.reset();
          setEntryFocus({ agentId: bridge.agentId, name: bridge.name });
          setActionMessage(bridgeAlreadyExistsMessage(bridge));
        }
      }
    }
  }

  function updateImportField<K extends keyof ImportAgentInput>(key: K, value: ImportAgentInput[K]) {
    setImportForm((current) => ({ ...current, [key]: value }));
  }

  async function handleImport() {
    try {
      const agent = await importMutation.mutateAsync(importForm);
      setEntryFocus({ agentId: agent.agentId, name: agent.name });
      setActionMessage(`Imported ${agent.name}. Review its validation here before using the asset in experiments.`);
      setImportForm({
        agentId: "",
        name: "",
        description: "",
        framework: "openai-agents-sdk",
        defaultModel: "",
        entrypoint: "",
        tags: []
      });
    } catch {
      // Error state is surfaced through the shared notice area.
    }
  }

  async function handleValidation(agent: AgentRecord) {
    try {
      const run = await validationMutation.mutateAsync({
        agentId: agent.agentId,
        payload: validationPayload(agent)
      });
      setActionMessage(
        `Started validation run ${run.run_id} for ${agent.name}. Atlas will attach the latest validation evidence here so the asset handoff stays explicit.`
      );
    } catch {
      // Error state is surfaced through the shared notice area.
    }
  }

  return {
    actionMessage,
    agents,
    bootstrapMutation,
    entryFocus,
    errorMessage,
    existingClaudeBridge,
    focusedAgent,
    groups,
    handleBootstrap,
    handleImport,
    handleValidation,
    importForm,
    importMutation,
    isLoading,
    starterDatasetMutation,
    updateImportField,
    validationBacklog,
    validationMutation
  };
}
