"use client";

import { ArrowUpRight, Boxes, ClipboardList } from "lucide-react";
import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { getArtifactDownloadUrl } from "@/src/entities/artifact/api";
import { useArtifactsQuery } from "@/src/entities/artifact/query";
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
  const artifactsQuery = useArtifactsQuery();
  const datasetsQuery = useDatasetsQuery();
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
  const runRecords = runsQuery.data ?? [];

  useEffect(() => {
    setActionMessage("");
  }, [requestFilters, runsQuery.dataUpdatedAt, runsQuery.errorUpdatedAt]);

  const message = actionMessage || (
    runsQuery.isPending
      ? "Loading runs..."
      : runsQuery.isError
        ? "Runs unavailable. Check the API connection and try again."
        : runRecords.length
          ? `Loaded ${runRecords.length} runs.`
          : "No runs found."
  );

  const deferredQuery = useDeferredValue(filters.query);
  const filteredRuns = useMemo(() => filterRuns(runRecords, deferredQuery), [deferredQuery, runRecords]);
  const filterOptions = useMemo(() => getFilterOptions(runRecords), [runRecords]);
  const stats = useMemo(() => getRunStats(filteredRuns), [filteredRuns]);
  const recentArtifacts = (artifactsQuery.data ?? []).slice(0, 5);
  const defaultDatasetName = datasetsQuery.data?.[0]?.name;

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Runs index</p>
          <h2 className="section-title">Run dashboard</h2>
          <p className="kicker">
            Operate the run queue, filter execution history, and jump directly into a trajectory workspace.
          </p>
        </div>
        <div className="toolbar">
          <Button href="/evals" variant="secondary">
            <ClipboardList size={14} /> Batch Eval
          </Button>
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
          </div>
          <div className="toolbar">
            {runRecords[0] ? (
              <Button href={`/runs/${runRecords[0].runId}`} variant="ghost">
                Open latest run <ArrowUpRight size={14} />
              </Button>
            ) : null}
            <ArtifactExportActions runId={runRecords[0]?.runId} onExported={setActionMessage} />
          </div>
        </div>

        <RunFilters options={filterOptions} state={filters} onChange={setFilters} />
        <Notice>{message}</Notice>
      </Panel>

      <Panel>
        <div className="surface-header">
          <div>
            <p className="surface-kicker">Runs</p>
            <h3 className="panel-title">Select a run to inspect its trajectory, compare steps, or replay a failure</h3>
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
            <h3 className="panel-title">Recent exports with direct download links</h3>
          </div>
        </div>

        {artifactsQuery.isPending ? (
          <Notice>Loading artifact history...</Notice>
        ) : artifactsQuery.isError ? (
          <Notice>Artifact history unavailable.</Notice>
        ) : recentArtifacts.length ? (
          <div className="table-shell">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Format</th>
                  <th>Runs</th>
                  <th>Size</th>
                  <th>Created</th>
                  <th>Download</th>
                </tr>
              </thead>
              <tbody>
                {recentArtifacts.map((artifact) => (
                  <tr key={artifact.artifactId}>
                    <td className="mono">{artifact.artifactId.slice(0, 8)}</td>
                    <td>{artifact.format.toUpperCase()}</td>
                    <td>{artifact.runIds.length}</td>
                    <td>{artifact.sizeBytes} bytes</td>
                    <td>{new Date(artifact.createdAt).toLocaleString()}</td>
                    <td>
                      <a href={getArtifactDownloadUrl(artifact.artifactId)} target="_blank" rel="noreferrer">
                        Download
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Notice>No artifacts exported yet.</Notice>
        )}
      </Panel>
    </section>
  );
}
