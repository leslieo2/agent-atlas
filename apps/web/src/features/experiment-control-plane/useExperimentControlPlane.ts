"use client";

import { useEffect, useMemo, useState } from "react";
import type { CompareOutcome, CurationStatus, SampleJudgement, ScoringMode } from "@/src/shared/api/contract";
import { usePublishedAgentsQuery } from "@/src/entities/agent/query";
import { useDatasetsQuery } from "@/src/entities/dataset/query";
import {
  buildCompareLookup,
  matchesExperimentRunFilters
} from "@/src/entities/experiment/compare";
import type { ExperimentRunRecord } from "@/src/entities/experiment/model";
import {
  useCancelExperimentMutation,
  useCreateExperimentMutation,
  useExperimentCompareQuery,
  useExperimentRunsQuery,
  useExperimentsQuery,
  usePatchExperimentRunMutation,
  useStartExperimentMutation
} from "@/src/entities/experiment/query";
import { usePoliciesQuery } from "@/src/entities/policy/query";
import { canCurateRun, canSelectPublishedAgentForExperiment, datasetVersionOptionLabel, parseTags, type PatchRunPayload, uniqueStrings } from "./model";

type Args = {
  initialAgentId?: string;
  initialDatasetVersionId?: string;
  initialExperimentId?: string;
};

export function useExperimentControlPlane({
  initialAgentId = "",
  initialDatasetVersionId = "",
  initialExperimentId = ""
}: Args) {
  const publishedAgentsQuery = usePublishedAgentsQuery();
  const datasetsQuery = useDatasetsQuery();
  const policiesQuery = usePoliciesQuery();
  const experimentsQuery = useExperimentsQuery();
  const createExperimentMutation = useCreateExperimentMutation();
  const startExperimentMutation = useStartExperimentMutation();
  const cancelExperimentMutation = useCancelExperimentMutation();
  const isAgentsLoading = publishedAgentsQuery.isPending;

  const agents = useMemo(
    () =>
      (publishedAgentsQuery.data ?? [])
        .filter((agent) => canSelectPublishedAgentForExperiment(agent))
        .map((agent) => ({
          agentId: agent.agentId,
          name: agent.name,
          defaultModel: agent.defaultModel,
          executionProfile: agent.executionProfile
        })),
    [publishedAgentsQuery.data]
  );
  const datasets = useMemo(() => datasetsQuery.data ?? [], [datasetsQuery.data]);
  const policies = useMemo(() => policiesQuery.data ?? [], [policiesQuery.data]);
  const experiments = useMemo(() => experimentsQuery.data ?? [], [experimentsQuery.data]);

  const datasetVersions = useMemo(
    () =>
      datasets.flatMap((dataset) =>
        dataset.versions.map((version) => ({
          ...version,
          datasetLabel: datasetVersionOptionLabel(dataset.name, version.version)
        }))
      ),
    [datasets]
  );

  const [agentId, setAgentId] = useState(initialAgentId);
  const [datasetVersionId, setDatasetVersionId] = useState(initialDatasetVersionId);
  const [model, setModel] = useState("");
  const [scoringMode, setScoringMode] = useState<ScoringMode>("exact_match");
  const [approvalPolicyId, setApprovalPolicyId] = useState("");
  const [tagsText, setTagsText] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [selectedExperimentId, setSelectedExperimentId] = useState(initialExperimentId);
  const [baselineExperimentId, setBaselineExperimentId] = useState("");
  const [judgementFilter, setJudgementFilter] = useState<SampleJudgement | "">("");
  const [errorCodeFilter, setErrorCodeFilter] = useState("");
  const [sliceFilter, setSliceFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [curationFilter, setCurationFilter] = useState<CurationStatus | "">("");
  const [compareOutcomeFilter, setCompareOutcomeFilter] = useState<CompareOutcome | "">("");
  const [actionMessage, setActionMessage] = useState("");

  const selectedExperiment = useMemo(
    () => experiments.find((item) => item.experimentId === selectedExperimentId) ?? experiments[0] ?? null,
    [experiments, selectedExperimentId]
  );
  const runsQuery = useExperimentRunsQuery(selectedExperiment?.experimentId ?? "");
  const patchRunMutation = usePatchExperimentRunMutation(selectedExperiment?.experimentId ?? "");
  const compareQuery = useExperimentCompareQuery(baselineExperimentId, selectedExperiment?.experimentId ?? "");
  const runs = useMemo(() => runsQuery.data ?? [], [runsQuery.data]);
  const compareSamples = useMemo(() => compareQuery.data?.samples ?? [], [compareQuery.data?.samples]);
  const compareLookup = useMemo(() => buildCompareLookup(compareSamples), [compareSamples]);

  const baselineOptions = useMemo(
    () =>
      experiments.filter(
        (item) =>
          selectedExperiment &&
          item.datasetVersionId === selectedExperiment.datasetVersionId &&
          item.experimentId !== selectedExperiment.experimentId
      ),
    [experiments, selectedExperiment]
  );
  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.agentId === agentId) ?? null,
    [agentId, agents]
  );

  const filteredRuns = useMemo(
    () =>
      runs.filter((run) =>
        matchesExperimentRunFilters({
          run,
          judgementFilter,
          errorCodeFilter,
          sliceFilter,
          tagFilter,
          curationFilter,
          compareLookup,
          compareOutcomeFilter
        })
      ),
    [
      runs,
      judgementFilter,
      errorCodeFilter,
      sliceFilter,
      tagFilter,
      curationFilter,
      compareLookup,
      compareOutcomeFilter
    ]
  );

  const sliceOptions = useMemo(() => uniqueStrings(runs.map((run) => run.slice)), [runs]);
  const tagOptions = useMemo(() => uniqueStrings(runs.flatMap((run) => run.tags)), [runs]);
  const errorCodeOptions = useMemo(() => uniqueStrings(runs.map((run) => run.errorCode)), [runs]);

  useEffect(() => {
    setAgentId(initialAgentId);
  }, [initialAgentId]);

  useEffect(() => {
    setDatasetVersionId(initialDatasetVersionId);
  }, [initialDatasetVersionId]);

  useEffect(() => {
    setSelectedExperimentId(initialExperimentId);
  }, [initialExperimentId]);

  useEffect(() => {
    if (!agents.length) {
      if (!isAgentsLoading && agentId) {
        setAgentId("");
      }
      return;
    }
    if (agentId && agents.some((agent) => agent.agentId === agentId)) {
      return;
    }
    setAgentId(agents[0].agentId);
  }, [agentId, agents, isAgentsLoading]);

  useEffect(() => {
    if (!datasetVersionId && datasetVersions[0]) {
      setDatasetVersionId(datasetVersions[0].datasetVersionId);
    }
  }, [datasetVersionId, datasetVersions]);

  useEffect(() => {
    if (!approvalPolicyId && policies[0]) {
      setApprovalPolicyId(policies[0].approvalPolicyId);
    }
  }, [approvalPolicyId, policies]);

  useEffect(() => {
    setModel(selectedAgent?.defaultModel ?? "");
  }, [selectedAgent?.agentId, selectedAgent?.defaultModel]);

  useEffect(() => {
    if (!baselineOptions.length) {
      setBaselineExperimentId("");
      return;
    }
    if (baselineExperimentId && baselineOptions.some((item) => item.experimentId === baselineExperimentId)) {
      return;
    }
    setBaselineExperimentId(baselineOptions[0]?.experimentId ?? "");
  }, [baselineExperimentId, baselineOptions]);

  const handleCreateExperiment = async () => {
    if (!agentId || !datasetVersionId) {
      setActionMessage("Select a governed asset and dataset version before creating an experiment.");
      return;
    }

    const version = datasetVersions.find((item) => item.datasetVersionId === datasetVersionId);
    const created = await createExperimentMutation.mutateAsync({
      name: `${agentId}-${version?.version ?? "latest"}`,
      datasetVersionId,
      publishedAgentId: agentId,
      model,
      scoringMode,
      approvalPolicyId: approvalPolicyId || null,
      systemPrompt,
      promptVersion: version?.version ?? "v1",
      tags: parseTags(tagsText)
    });
    await startExperimentMutation.mutateAsync(created.experimentId);
    setSelectedExperimentId(created.experimentId);
    setActionMessage(`Created and started experiment ${created.experimentId}.`);
  };

  const handlePatchRun = async (run: ExperimentRunRecord, payload: PatchRunPayload) => {
    if (!canCurateRun(run)) {
      setActionMessage(`Wait for ${run.datasetSampleId} to finish before changing its curation state.`);
      return;
    }

    try {
      await patchRunMutation.mutateAsync({
        runId: run.runId,
        payload: {
          curationStatus: payload.curationStatus ?? run.curationStatus,
          curationNote: run.curationNote ?? null,
          exportEligible: payload.exportEligible ?? run.exportEligible ?? false
        }
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to update the run curation state.";
      setActionMessage(message || "Unable to update the run curation state.");
    }
  };

  return {
    actionMessage,
    agentId,
    agents,
    approvalPolicyId,
    baselineExperimentId,
    baselineOptions,
    cancelExperimentMutation,
    compareLookup,
    compareOutcomeFilter,
    compareQuery,
    createExperimentMutation,
    curationFilter,
    datasetVersionId,
    datasetVersions,
    errorCodeFilter,
    errorCodeOptions,
    experiments,
    experimentsQuery,
    filteredRuns,
    handleCreateExperiment,
    handlePatchRun,
    isAgentsLoading,
    judgementFilter,
    model,
    patchRunMutation,
    policies,
    runsQuery,
    scoringMode,
    selectedAgent,
    selectedExperiment,
    selectedExperimentId,
    setAgentId,
    setApprovalPolicyId,
    setBaselineExperimentId,
    setCompareOutcomeFilter,
    setCurationFilter,
    setDatasetVersionId,
    setErrorCodeFilter,
    setJudgementFilter,
    setModel,
    setScoringMode,
    setSelectedExperimentId,
    setSliceFilter,
    setSystemPrompt,
    setTagFilter,
    setTagsText,
    sliceFilter,
    sliceOptions,
    startExperimentMutation,
    systemPrompt,
    tagFilter,
    tagOptions,
    tagsText
  };
}
