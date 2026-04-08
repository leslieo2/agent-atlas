"use client";

import { ArrowUpRight } from "lucide-react";
import { DatasetCatalogPanel, DatasetIngestPanel } from "@/src/features/dataset-control-plane/DatasetPanels";
import { useDatasetControlPlane } from "@/src/features/dataset-control-plane/useDatasetControlPlane";
import { MetricCard } from "@/src/shared/ui/MetricCard";
import { Button } from "@/src/shared/ui/Button";
import { Notice } from "@/src/shared/ui/Notice";
import styles from "./DatasetsWorkspace.module.css";

export default function DatasetsWorkspace() {
  const controlPlane = useDatasetControlPlane();

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">RL data assets</p>
          <h2 className="section-title">Datasets</h2>
          <p className="kicker">
            Treat datasets as source-of-truth training assets. Define slices, provenance, and export eligibility before
            you fan out experiments.
          </p>
          <div className="page-tag-list">
            <span className="page-tag">
              Datasets <strong>{controlPlane.datasets.length}</strong>
            </span>
            <span className="page-tag">
              Samples <strong>{controlPlane.totalSamples}</strong>
            </span>
            <span className="page-tag">
              Export-ready <strong>{controlPlane.exportEligibleCount}</strong>
            </span>
          </div>
        </div>
        <div className="page-info-grid">
          <div className="page-info-item">
            <span className="page-info-label">Selected dataset</span>
            <span className="page-info-value">{controlPlane.selectedDatasetRecord?.name ?? "Waiting for dataset import"}</span>
            <p className="page-info-detail">
              {controlPlane.selectedDatasetRecord
                ? controlPlane.datasetSummary(controlPlane.selectedDatasetRecord)
                : "Import JSONL to create the next dataset asset for experiments and exports."}
            </p>
          </div>
          <div className="toolbar">
            {controlPlane.selectedDatasetRecord ? (
              <Button
                href={
                  controlPlane.selectedDatasetRecord.currentVersionId
                    ? `/experiments?datasetVersion=${encodeURIComponent(controlPlane.selectedDatasetRecord.currentVersionId)}`
                    : "/experiments"
                }
                variant="secondary"
              >
                Open in experiments <ArrowUpRight size={14} />
              </Button>
            ) : null}
          </div>
        </div>
      </header>

      <div className="summary-strip">
        <MetricCard label="Dataset count" value={controlPlane.datasets.length} />
        <MetricCard label="Total samples" value={controlPlane.totalSamples} />
        <MetricCard label="Selected rows" value={controlPlane.filteredRows.length} />
        <MetricCard label="Slices" value={controlPlane.sliceOptions.length} />
        <MetricCard label="Sources" value={controlPlane.sourceOptions.length} />
      </div>

      {controlPlane.feedback ? (
        <Notice>
          {controlPlane.feedback}{" "}
          {controlPlane.latestImportedDatasetVersionId ? (
            <Button
              href={`/experiments?datasetVersion=${encodeURIComponent(controlPlane.latestImportedDatasetVersionId)}`}
              variant="ghost"
            >
              Open imported dataset in experiments
            </Button>
          ) : null}
        </Notice>
      ) : null}

      <div className={styles.workspaceGrid}>
        <DatasetIngestPanel
          createPending={controlPlane.createDatasetMutation.isPending}
          datasetDescription={controlPlane.datasetDescription}
          datasetName={controlPlane.datasetName}
          datasetSource={controlPlane.datasetSource}
          datasetVersion={controlPlane.datasetVersion}
          fileInputRef={controlPlane.fileInputRef}
          onClearPendingUpload={controlPlane.clearPendingUpload}
          onDatasetDescriptionChange={controlPlane.setDatasetDescription}
          onDatasetNameChange={controlPlane.setDatasetName}
          onDatasetSourceChange={controlPlane.setDatasetSource}
          onDatasetUpload={controlPlane.handleDatasetUpload}
          onDatasetVersionChange={controlPlane.setDatasetVersion}
          onImportPendingUpload={() => void controlPlane.handleImportPendingUpload()}
          pendingUpload={controlPlane.pendingUpload}
          styles={styles}
        />

        <DatasetCatalogPanel
          datasetVersionLabel={controlPlane.datasetVersionLabel}
          datasets={controlPlane.datasets}
          datasetsQueryError={controlPlane.datasetsQuery.isError}
          datasetsQueryPending={controlPlane.datasetsQuery.isPending}
          onSelectedDatasetChange={controlPlane.setSelectedDataset}
          onSliceFilterChange={controlPlane.setSliceFilter}
          onSourceFilterChange={controlPlane.setSourceFilter}
          onTagFilterChange={controlPlane.setTagFilter}
          previewRows={controlPlane.previewRows}
          selectedDataset={controlPlane.selectedDataset}
          selectedDatasetRecord={controlPlane.selectedDatasetRecord}
          sliceFilter={controlPlane.sliceFilter}
          sliceOptions={controlPlane.sliceOptions}
          sourceFilter={controlPlane.sourceFilter}
          sourceOptions={controlPlane.sourceOptions}
          styles={styles}
          tagFilter={controlPlane.tagFilter}
          tagOptions={controlPlane.tagOptions}
        />
      </div>
    </section>
  );
}
