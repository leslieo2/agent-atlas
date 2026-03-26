"use client";

import { ArrowUpRight, Boxes } from "lucide-react";
import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { getArtifactDownloadUrl } from "@/src/entities/artifact/api";
import { useArtifactsQuery } from "@/src/entities/artifact/query";
import {
  formatArtifactDate,
  formatArtifactRunCount,
  formatArtifactSize
} from "@/src/entities/artifact/presentation";
import { useDatasetsQuery } from "@/src/entities/dataset/query";
import { useRunsQuery } from "@/src/entities/run/query";
import { ArtifactExportActions } from "@/src/features/artifact-export/ArtifactExportActions";
import { RunCreateButton } from "@/src/features/run-create/RunCreateButton";
import { RunFilters, type RunFilterState, buildRunFilters } from "@/src/features/run-filters/RunFilters";
import { RunTable } from "@/src/features/run-table/RunTable";
import { Button } from "@/src/shared/ui/Button";
import { MetricCard } from "@/src/shared/ui/MetricCard";
import { Notice } from "@/src/shared/ui/Notice";
import { Panel } from "@/src/shared/ui/Panel";
import { getFilterOptions, getRunStats, filterRuns } from "./selectors";
import styles from "./RunDashboardWidget.module.css";

const defaultFilterState: RunFilterState = {
  projectFilter: "all",
  datasetFilter: "all",
  agentFilter: "all",
  modelFilter: "all",
  statusFilter: "all",
  tagFilter: "all",
  createdFrom: "",
  createdTo: "",
  query: ""
};

export default function RunDashboardWidget() {
  const [actionMessage, setActionMessage] = useState("");
  const [filters, setFilters] = useState<RunFilterState>(defaultFilterState);
  const datasetsQuery = useDatasetsQuery();
  const artifactsQuery = useArtifactsQuery();
  const { projectFilter, datasetFilter, agentFilter, modelFilter, statusFilter, tagFilter, createdFrom, createdTo } =
    filters;
  const requestFilters = useMemo(
    () =>
      buildRunFilters({
        ...defaultFilterState,
        projectFilter,
        datasetFilter,
        agentFilter,
        modelFilter,
        statusFilter,
        tagFilter,
        createdFrom,
        createdTo
      }),
    [projectFilter, datasetFilter, agentFilter, modelFilter, statusFilter, tagFilter, createdFrom, createdTo]
  );
  const runsQuery = useRunsQuery(requestFilters);
  const runRecords = useMemo(() => runsQuery.data ?? [], [runsQuery.data]);

  useEffect(() => {
    setActionMessage("");
  }, [requestFilters, runsQuery.dataUpdatedAt, runsQuery.errorUpdatedAt]);

  const message =
    actionMessage ||
    (runsQuery.isPending
      ? "Loading runs..."
      : runsQuery.isError
        ? "Runs unavailable. Check the API connection and try again."
        : runRecords.length
          ? `Loaded ${runRecords.length} runs.`
          : "No runs found.");

  const deferredQuery = useDeferredValue(filters.query);
  const filteredRuns = useMemo(() => filterRuns(runRecords, deferredQuery), [deferredQuery, runRecords]);
  const filteredRunIds = useMemo(() => filteredRuns.map((run) => run.runId), [filteredRuns]);
  const filterOptions = useMemo(() => getFilterOptions(runRecords), [runRecords]);
  const stats = useMemo(() => getRunStats(filteredRuns), [filteredRuns]);
  const defaultDatasetName = datasetsQuery.data?.[0]?.name;
  const latestRun = runRecords[0];
  const recentArtifacts = useMemo(() => (artifactsQuery.data ?? []).slice(0, 6), [artifactsQuery.data]);

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Runs index</p>
          <h2 className="section-title">Run dashboard</h2>
          <p className="kicker">
            Operate the run queue, filter execution history, and jump directly into a trajectory workspace.
          </p>
          <div className="page-tag-list">
            <span className="page-tag">
              Indexed runs <strong>{runRecords.length}</strong>
            </span>
            <span className="page-tag">
              Projects <strong>{filterOptions.projects.length || 0}</strong>
            </span>
            <span className="page-tag">
              Datasets <strong>{filterOptions.datasets.length || 0}</strong>
            </span>
          </div>
        </div>
        <div className="page-info-grid">
          <div className="page-info-item">
            <span className="page-info-label">Queue snapshot</span>
            <span className="page-info-value">
              {stats.running} running / {stats.failed} failed
            </span>
            <p className="page-info-detail">
              {latestRun
                ? `Latest run ${latestRun.runId} in ${latestRun.project}.`
                : "Waiting for the first recorded run."}
            </p>
          </div>
          <div className="toolbar">
            <Button href="/playground" variant="secondary">
              <Boxes size={14} /> Playground
            </Button>
            <RunCreateButton
              datasetName={defaultDatasetName}
              onCreated={() => {
                setActionMessage("Opening Playground with the selected dataset.");
              }}
            />
          </div>
        </div>
      </header>

      <div className="summary-strip">
        <MetricCard label="Visible runs" value={stats.total} />
        <MetricCard label="Running" value={stats.running} />
        <MetricCard label="Failed" value={stats.failed} />
        <MetricCard label="Avg latency" value={`${stats.avgLatency} ms`} />
      </div>

      <Panel tone="strong">
        <div className="surface-header">
          <div>
            <p className="surface-kicker">Filters</p>
            <h3 className="panel-title">Search by project, dataset, agent, model, tag, and time range</h3>
            <p className="muted-note">
              Use server-side filters for time and status, then narrow locally with text search.
            </p>
          </div>
          <div className="toolbar">
            {latestRun ? (
              <Button href={`/runs/${latestRun.runId}`} variant="ghost">
                Open latest run <ArrowUpRight size={14} />
              </Button>
            ) : null}
            <ArtifactExportActions runIds={filteredRunIds} />
          </div>
        </div>

        <RunFilters options={filterOptions} state={filters} onChange={setFilters} />
        <Notice>{message}</Notice>
      </Panel>

      <Panel>
        <div className="surface-header">
          <div>
            <p className="surface-kicker">Runs</p>
            <h3 className="panel-title">Select a run to inspect its trajectory and execution details</h3>
            <p className="muted-note">
              The table keeps the full execution context visible so you can pivot straight into trajectory review.
            </p>
          </div>
        </div>

        <RunTable
          rows={filteredRuns}
          message={filteredRuns.length === 0 && runRecords.length > 0 ? "No runs match current filters." : message}
        />
      </Panel>

      <Panel>
        <div className="surface-header">
          <div>
            <p className="surface-kicker">Artifacts</p>
            <h3 className="panel-title">Artifact history</h3>
            <p className="muted-note">
              Review recent JSONL and parquet exports without leaving the dashboard.
            </p>
          </div>
        </div>

        <div className={styles.artifactHistory}>
          {artifactsQuery.isPending ? <Notice>Loading artifact history...</Notice> : null}
          {artifactsQuery.isError ? <Notice>Artifact history is temporarily unavailable.</Notice> : null}
          {!artifactsQuery.isPending && !artifactsQuery.isError && recentArtifacts.length === 0 ? (
            <Notice>No exported artifacts yet.</Notice>
          ) : null}
          {recentArtifacts.length ? (
            <div className={styles.artifactRows}>
              {recentArtifacts.map((artifact) => (
                <article key={artifact.artifactId} className={styles.artifactRow}>
                  <div className={styles.artifactPrimary}>
                    <strong className={`${styles.artifactId} mono`}>{artifact.artifactId}</strong>
                    <div className={styles.artifactMeta}>
                      <span>{artifact.format.toUpperCase()}</span>
                      <span>{formatArtifactRunCount(artifact)}</span>
                      <span>{formatArtifactSize(artifact.sizeBytes)}</span>
                    </div>
                  </div>
                  <div className={styles.artifactSecondary}>
                    <span className="page-eyebrow">Exported</span>
                    <span className="muted-note">{formatArtifactDate(artifact.createdAt)}</span>
                  </div>
                  <Button href={getArtifactDownloadUrl(artifact.artifactId)} variant="ghost">
                    Download {artifact.format.toUpperCase()} artifact
                  </Button>
                </article>
              ))}
            </div>
          ) : null}
        </div>
      </Panel>
    </section>
  );
}
