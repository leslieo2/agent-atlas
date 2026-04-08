"use client";

import { useExportControlPlane } from "@/src/features/export-control-plane/useExportControlPlane";
import { ExportBuilderPanel, ExportHistoryPanel } from "@/src/features/export-control-plane/ExportPanels";
import styles from "./ExportsWorkspace.module.css";

type Props = {
  initialExperimentId?: string;
  initialBaselineExperimentId?: string;
  initialCandidateExperimentId?: string;
};

export default function ExportsWorkspace({
  initialExperimentId = "",
  initialBaselineExperimentId = "",
  initialCandidateExperimentId = ""
}: Props) {
  const controlPlane = useExportControlPlane({
    initialExperimentId,
    initialBaselineExperimentId,
    initialCandidateExperimentId
  });

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Offline handoff</p>
          <h2 className="section-title">Exports</h2>
          <p className="kicker">
            Convert evidence-backed experiment runs into RL-ready offline files. Export only the rows that survive
            compare, curation, and lineage filters.
          </p>
          <div className="page-tag-list">
            <span className="page-tag">
              Exports <strong>{(controlPlane.exportsQuery.data ?? []).length}</strong>
            </span>
            <span className="page-tag">
              Source dataset <strong>{controlPlane.sourceExperiment?.datasetName ?? "none"}</strong>
            </span>
            <span className="page-tag">
              Source runs <strong>{controlPlane.runs.length}</strong>
            </span>
          </div>
        </div>
        <div className="page-info-grid">
          <div className="page-info-item">
            <span className="page-info-label">Current source</span>
            <span className="page-info-value">
              {controlPlane.sourceExperiment
                ? `${controlPlane.sourceExperiment.publishedAgentId} on ${controlPlane.sourceExperiment.datasetName}`
                : "Waiting for selection"}
            </span>
            <p className="page-info-detail">
              {controlPlane.candidateExperimentId
                ? "Compare-aware export mode is active. Finalize the preview rows, then create the handoff file."
                : "Pick one experiment first, then tighten the preview rows before creating the handoff file."}
            </p>
          </div>
        </div>
      </header>

      <div className={styles.workspaceGrid}>
        <ExportBuilderPanel
          actionMessage={controlPlane.actionMessage}
          activeFilters={controlPlane.activeFilters}
          baselineExperimentId={controlPlane.baselineExperimentId}
          baselineOptions={controlPlane.baselineOptions}
          candidateExperimentId={controlPlane.candidateExperimentId}
          compareOutcomeFilter={controlPlane.compareOutcomeFilter}
          createPending={controlPlane.createExportMutation.isPending}
          curationFilter={controlPlane.curationFilter}
          errorCodeFilter={controlPlane.errorCodeFilter}
          errorCodeOptions={controlPlane.errorCodeOptions}
          experimentId={controlPlane.experimentId}
          experiments={controlPlane.experiments}
          exportEligibleOnly={controlPlane.exportEligibleOnly}
          format={controlPlane.format}
          judgementFilter={controlPlane.judgementFilter}
          latestExportId={controlPlane.latestExportId}
          onBaselineExperimentIdChange={controlPlane.setBaselineExperimentId}
          onCandidateExperimentIdChange={controlPlane.setCandidateExperimentId}
          onCompareOutcomeFilterChange={controlPlane.setCompareOutcomeFilter}
          onCreateExport={() => void controlPlane.handleCreateExport()}
          onCurationFilterChange={controlPlane.setCurationFilter}
          onErrorCodeFilterChange={controlPlane.setErrorCodeFilter}
          onExperimentIdChange={controlPlane.setExperimentId}
          onExportEligibleOnlyChange={controlPlane.setExportEligibleOnly}
          onFormatChange={controlPlane.setFormat}
          onJudgementFilterChange={controlPlane.setJudgementFilter}
          onResetFilters={controlPlane.handleResetFilters}
          onSliceFilterChange={controlPlane.setSliceFilter}
          onTagFilterChange={controlPlane.setTagFilter}
          previewReviewCount={controlPlane.previewReviewCount}
          previewRowsCount={controlPlane.previewRows.length}
          runsCount={controlPlane.runs.length}
          sliceFilter={controlPlane.sliceFilter}
          sliceOptions={controlPlane.sliceOptions}
          sourceExperiment={controlPlane.sourceExperiment}
          styles={styles}
          tagFilter={controlPlane.tagFilter}
          tagOptions={controlPlane.tagOptions}
        />

        <ExportHistoryPanel
          exports={controlPlane.exportsQuery.data ?? []}
          isError={controlPlane.exportsQuery.isError}
          isPending={controlPlane.exportsQuery.isPending}
          styles={styles}
        />
      </div>
    </section>
  );
}
