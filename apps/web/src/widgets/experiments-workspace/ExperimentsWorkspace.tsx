"use client";

import { MetricCard } from "@/src/shared/ui/MetricCard";
import { useExperimentControlPlane } from "@/src/features/experiment-control-plane/useExperimentControlPlane";
import {
  ExperimentComparePanel,
  ExperimentCreatePanel,
  ExperimentRunsPanel,
  ExperimentSelectionPanels
} from "@/src/features/experiment-control-plane/ExperimentPanels";
import styles from "./ExperimentsWorkspace.module.css";

type Props = {
  initialAgentId?: string;
  initialDatasetVersionId?: string;
  initialExperimentId?: string;
};

export default function ExperimentsWorkspace({
  initialAgentId = "",
  initialDatasetVersionId = "",
  initialExperimentId = ""
}: Props) {
  const controlPlane = useExperimentControlPlane({
    initialAgentId,
    initialDatasetVersionId,
    initialExperimentId
  });

  return (
    <div className={styles.workspace}>
      <div className={styles.hero}>
        <div>
          <p className="page-eyebrow">Experiment control plane</p>
          <h2 className="page-title">Governance to evidence loop</h2>
          <p className="muted-note">
            Atlas turns governed assets into runs, evidence, and curated exports without promoting provider,
            runner, or credential internals into the product center. Phoenix remains a deeplink for deeper trace inspection.
          </p>
        </div>
        <div className={styles.metricGrid}>
          <MetricCard label="Experiments" value={controlPlane.experiments.length} />
          <MetricCard label="Runs in view" value={controlPlane.filteredRuns.length} />
          <MetricCard label="Policies" value={controlPlane.policies.length} />
        </div>
      </div>

      <ExperimentCreatePanel
        actionMessage={controlPlane.actionMessage}
        agentId={controlPlane.agentId}
        agents={controlPlane.agents}
        approvalPolicyId={controlPlane.approvalPolicyId}
        createPending={controlPlane.createExperimentMutation.isPending}
        datasetVersionId={controlPlane.datasetVersionId}
        datasetVersions={controlPlane.datasetVersions}
        isAgentsLoading={controlPlane.isAgentsLoading}
        model={controlPlane.model}
        onAgentIdChange={controlPlane.setAgentId}
        onApprovalPolicyIdChange={controlPlane.setApprovalPolicyId}
        onCreateExperiment={() => void controlPlane.handleCreateExperiment()}
        onDatasetVersionIdChange={controlPlane.setDatasetVersionId}
        onModelChange={controlPlane.setModel}
        onScoringModeChange={controlPlane.setScoringMode}
        onSystemPromptChange={controlPlane.setSystemPrompt}
        onTagsTextChange={controlPlane.setTagsText}
        policies={controlPlane.policies}
        scoringMode={controlPlane.scoringMode}
        selectedAgent={controlPlane.selectedAgent}
        styles={styles}
        systemPrompt={controlPlane.systemPrompt}
        tagsText={controlPlane.tagsText}
      />

      <ExperimentSelectionPanels
        cancelPending={controlPlane.cancelExperimentMutation.isPending}
        experiments={controlPlane.experiments}
        experimentsPending={controlPlane.experimentsQuery.isPending}
        filteredRunsCount={controlPlane.filteredRuns.length}
        onCancel={(experimentId) => void controlPlane.cancelExperimentMutation.mutateAsync(experimentId)}
        onSelectExperiment={controlPlane.setSelectedExperimentId}
        policiesCount={controlPlane.policies.length}
        selectedExperiment={controlPlane.selectedExperiment}
        styles={styles}
      />

      <ExperimentComparePanel
        baselineExperimentId={controlPlane.baselineExperimentId}
        baselineOptions={controlPlane.baselineOptions}
        compareDistribution={controlPlane.compareQuery.data?.distribution}
        onBaselineExperimentIdChange={controlPlane.setBaselineExperimentId}
        styles={styles}
      />

      <ExperimentRunsPanel
        baselineExperimentId={controlPlane.baselineExperimentId}
        compareLookup={controlPlane.compareLookup}
        compareOutcomeFilter={controlPlane.compareOutcomeFilter}
        curationFilter={controlPlane.curationFilter}
        errorCodeFilter={controlPlane.errorCodeFilter}
        errorCodeOptions={controlPlane.errorCodeOptions}
        filteredRuns={controlPlane.filteredRuns}
        judgementFilter={controlPlane.judgementFilter}
        onCompareOutcomeFilterChange={controlPlane.setCompareOutcomeFilter}
        onCurationFilterChange={controlPlane.setCurationFilter}
        onErrorCodeFilterChange={controlPlane.setErrorCodeFilter}
        onJudgementFilterChange={controlPlane.setJudgementFilter}
        onPatchRun={(run, payload) => void controlPlane.handlePatchRun(run, payload)}
        onSliceFilterChange={controlPlane.setSliceFilter}
        onTagFilterChange={controlPlane.setTagFilter}
        patchPending={controlPlane.patchRunMutation.isPending}
        runsPending={controlPlane.runsQuery.isPending}
        selectedExperiment={controlPlane.selectedExperiment}
        sliceFilter={controlPlane.sliceFilter}
        sliceOptions={controlPlane.sliceOptions}
        styles={styles}
        tagFilter={controlPlane.tagFilter}
        tagOptions={controlPlane.tagOptions}
      />
    </div>
  );
}
