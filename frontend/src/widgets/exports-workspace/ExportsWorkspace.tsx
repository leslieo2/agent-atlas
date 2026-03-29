"use client";

import { Download, RotateCcw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { getExportDownloadUrl } from "@/src/entities/export/api";
import { useCreateExportMutation, useExportsQuery } from "@/src/entities/export/query";
import type { ExperimentRunRecord } from "@/src/entities/experiment/model";
import {
  useExperimentCompareQuery,
  useExperimentRunsQuery,
  useExperimentsQuery
} from "@/src/entities/experiment/query";
import type { CompareOutcome, CurationStatus, SampleJudgement } from "@/src/shared/api/contract";
import { Button } from "@/src/shared/ui/Button";
import { Field } from "@/src/shared/ui/Field";
import { Notice } from "@/src/shared/ui/Notice";
import { Panel } from "@/src/shared/ui/Panel";
import { TableShell } from "@/src/shared/ui/TableShell";
import styles from "./ExportsWorkspace.module.css";

type Props = {
  initialExperimentId?: string;
  initialBaselineExperimentId?: string;
  initialCandidateExperimentId?: string;
};

function uniqueStrings(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value)))).sort();
}

function formatTimestamp(value: string) {
  return new Date(value).toLocaleString("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

function formatBytes(value: number) {
  if (!Number.isFinite(value) || value <= 0) {
    return "0 B";
  }

  if (value < 1024) {
    return `${value} B`;
  }

  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }

  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function buildActiveFilters(filters: {
  judgementFilter: string;
  errorCodeFilter: string;
  sliceFilter: string;
  tagFilter: string;
  compareOutcomeFilter: string;
  curationFilter: string;
  exportEligibleOnly: boolean;
}) {
  return [
    filters.judgementFilter ? `Judgement: ${filters.judgementFilter}` : null,
    filters.errorCodeFilter ? `Error: ${filters.errorCodeFilter}` : null,
    filters.sliceFilter ? `Slice: ${filters.sliceFilter}` : null,
    filters.tagFilter ? `Tag: ${filters.tagFilter}` : null,
    filters.compareOutcomeFilter ? `Compare: ${filters.compareOutcomeFilter}` : null,
    filters.curationFilter ? `Curation: ${filters.curationFilter}` : null,
    filters.exportEligibleOnly ? null : "Eligibility: include ineligible rows"
  ].filter((value): value is string => Boolean(value));
}

function matchesPreviewFilters({
  run,
  compareOutcome,
  judgementFilter,
  errorCodeFilter,
  sliceFilter,
  tagFilter,
  compareOutcomeFilter,
  curationFilter,
  exportEligibleOnly
}: {
  run: ExperimentRunRecord;
  compareOutcome?: CompareOutcome | null;
  judgementFilter: string;
  errorCodeFilter: string;
  sliceFilter: string;
  tagFilter: string;
  compareOutcomeFilter: string;
  curationFilter: string;
  exportEligibleOnly: boolean;
}) {
  if (judgementFilter && run.judgement !== judgementFilter) {
    return false;
  }
  if (errorCodeFilter && run.errorCode !== errorCodeFilter) {
    return false;
  }
  if (sliceFilter && run.slice !== sliceFilter) {
    return false;
  }
  if (tagFilter && !run.tags.includes(tagFilter)) {
    return false;
  }
  if (compareOutcomeFilter && compareOutcome !== compareOutcomeFilter) {
    return false;
  }
  if (curationFilter && run.curationStatus !== curationFilter) {
    return false;
  }
  if (exportEligibleOnly && run.exportEligible === false) {
    return false;
  }
  return true;
}

function formatFilterSummaryValue(value: unknown) {
  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "none";
  }
  if (typeof value === "boolean") {
    return value ? "yes" : "no";
  }
  if (value == null || value === "") {
    return "none";
  }
  return String(value);
}

function summarizeFilterSummary(filtersSummary: Record<string, unknown>) {
  const entries = Object.entries(filtersSummary);
  if (!entries.length) {
    return ["Default export rules"];
  }

  return entries.map(([key, value]) => `${key}: ${formatFilterSummaryValue(value)}`);
}

export default function ExportsWorkspace({
  initialExperimentId = "",
  initialBaselineExperimentId = "",
  initialCandidateExperimentId = ""
}: Props) {
  const experimentsQuery = useExperimentsQuery();
  const exportsQuery = useExportsQuery();
  const createExportMutation = useCreateExportMutation();

  const [experimentId, setExperimentId] = useState(initialExperimentId);
  const [baselineExperimentId, setBaselineExperimentId] = useState(initialBaselineExperimentId);
  const [candidateExperimentId, setCandidateExperimentId] = useState(initialCandidateExperimentId);
  const [judgementFilter, setJudgementFilter] = useState("");
  const [errorCodeFilter, setErrorCodeFilter] = useState("");
  const [sliceFilter, setSliceFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [compareOutcomeFilter, setCompareOutcomeFilter] = useState("");
  const [curationFilter, setCurationFilter] = useState("");
  const [exportEligibleOnly, setExportEligibleOnly] = useState(true);
  const [format, setFormat] = useState<"jsonl" | "parquet">("jsonl");
  const [actionMessage, setActionMessage] = useState("");
  const [latestExportId, setLatestExportId] = useState<string | null>(null);

  const experiments = useMemo(() => experimentsQuery.data ?? [], [experimentsQuery.data]);
  const selectedSourceExperimentId = candidateExperimentId || experimentId;
  const sourceExperiment = useMemo(
    () => experiments.find((record) => record.experimentId === selectedSourceExperimentId) ?? null,
    [experiments, selectedSourceExperimentId]
  );
  const selectedRunsQuery = useExperimentRunsQuery(selectedSourceExperimentId);
  const compareQuery = useExperimentCompareQuery(baselineExperimentId, candidateExperimentId);
  const runs = useMemo(() => selectedRunsQuery.data ?? [], [selectedRunsQuery.data]);
  const compareLookup = useMemo(
    () =>
      new Map(
        (compareQuery.data?.samples ?? []).map((sample) => [sample.datasetSampleId, sample.compareOutcome] as const)
      ),
    [compareQuery.data?.samples]
  );

  const errorCodeOptions = useMemo(() => uniqueStrings(runs.map((run) => run.errorCode)), [runs]);
  const sliceOptions = useMemo(() => uniqueStrings(runs.map((run) => run.slice)), [runs]);
  const tagOptions = useMemo(() => uniqueStrings(runs.flatMap((run) => run.tags)), [runs]);
  const previewRows = useMemo(
    () =>
      runs.filter((run) =>
        matchesPreviewFilters({
          run,
          compareOutcome: compareLookup.get(run.datasetSampleId) ?? run.compareOutcome ?? null,
          judgementFilter,
          errorCodeFilter,
          sliceFilter,
          tagFilter,
          compareOutcomeFilter,
          curationFilter,
          exportEligibleOnly
        })
      ),
    [
      runs,
      compareLookup,
      judgementFilter,
      errorCodeFilter,
      sliceFilter,
      tagFilter,
      compareOutcomeFilter,
      curationFilter,
      exportEligibleOnly
    ]
  );
  const previewReviewCount = useMemo(
    () => previewRows.filter((run) => run.curationStatus === "review").length,
    [previewRows]
  );
  const activeFilters = useMemo(
    () =>
      buildActiveFilters({
        judgementFilter,
        errorCodeFilter,
        sliceFilter,
        tagFilter,
        compareOutcomeFilter,
        curationFilter,
        exportEligibleOnly
      }),
    [judgementFilter, errorCodeFilter, sliceFilter, tagFilter, compareOutcomeFilter, curationFilter, exportEligibleOnly]
  );
  const baselineOptions = useMemo(
    () =>
      sourceExperiment
        ? experiments.filter(
            (record) =>
              record.datasetVersionId === sourceExperiment.datasetVersionId &&
              record.experimentId !== sourceExperiment.experimentId
          )
        : [],
    [experiments, sourceExperiment]
  );

  useEffect(() => {
    if (!selectedSourceExperimentId && experiments[0]) {
      setExperimentId(experiments[0].experimentId);
    }
  }, [experiments, selectedSourceExperimentId]);

  useEffect(() => {
    if (candidateExperimentId) {
      return;
    }

    if (baselineExperimentId && baselineOptions.some((record) => record.experimentId === baselineExperimentId)) {
      return;
    }

    setBaselineExperimentId("");
  }, [baselineExperimentId, baselineOptions, candidateExperimentId]);

  const handleCreateExport = async () => {
    if (!selectedSourceExperimentId) {
      setActionMessage("Select an experiment source before creating an export.");
      return;
    }

    const exported = await createExportMutation.mutateAsync({
      experimentId: candidateExperimentId ? null : experimentId || null,
      baselineExperimentId: baselineExperimentId || null,
      candidateExperimentId: candidateExperimentId || null,
      datasetSampleIds: previewRows.map((run) => run.datasetSampleId),
      judgements: judgementFilter ? [judgementFilter as SampleJudgement] : null,
      errorCodes: errorCodeFilter ? [errorCodeFilter] : null,
      compareOutcomes: compareOutcomeFilter ? [compareOutcomeFilter as CompareOutcome] : null,
      tags: tagFilter ? [tagFilter] : null,
      slices: sliceFilter ? [sliceFilter] : null,
      curationStatuses: curationFilter ? [curationFilter as CurationStatus] : null,
      exportEligible: exportEligibleOnly,
      format
    });

    setLatestExportId(exported.exportId);
    setActionMessage(`Created export ${exported.exportId}.`);
  };

  const handleResetFilters = () => {
    setJudgementFilter("");
    setErrorCodeFilter("");
    setSliceFilter("");
    setTagFilter("");
    setCompareOutcomeFilter("");
    setCurationFilter("");
    setExportEligibleOnly(true);
  };

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Offline handoff</p>
          <h2 className="section-title">Exports</h2>
          <p className="kicker">
            Convert experiment runs into RL-ready offline files. Export only the rows that survive compare, curation,
            and lineage filters.
          </p>
          <div className="page-tag-list">
            <span className="page-tag">
              Exports <strong>{(exportsQuery.data ?? []).length}</strong>
            </span>
            <span className="page-tag">
              Source dataset <strong>{sourceExperiment?.datasetName ?? "none"}</strong>
            </span>
            <span className="page-tag">
              Source runs <strong>{runs.length}</strong>
            </span>
          </div>
        </div>
        <div className="page-info-grid">
          <div className="page-info-item">
            <span className="page-info-label">Current source</span>
            <span className="page-info-value">
              {sourceExperiment
                ? `${sourceExperiment.publishedAgentId} on ${sourceExperiment.datasetName}`
                : "Waiting for selection"}
            </span>
            <p className="page-info-detail">
              {candidateExperimentId
                ? "Compare-aware export mode is active."
                : "Export rows directly from one experiment or switch into compare-aware mode by selecting a candidate."}
            </p>
          </div>
        </div>
      </header>

      {actionMessage ? (
        <Notice>
          {actionMessage}{" "}
          {latestExportId ? (
            <Button href={getExportDownloadUrl(latestExportId)} variant="ghost">
              Download export
            </Button>
          ) : null}
        </Notice>
      ) : null}

      <div className={styles.workspaceGrid}>
        <Panel tone="strong">
          <div className="surface-header">
            <div>
              <p className="surface-kicker">Create export</p>
              <h3 className="panel-title">Filter experiment runs into a training file</h3>
              <p className="muted-note">
                This is the Atlas handoff surface. Phoenix explains failures; Atlas decides what leaves the platform.
              </p>
            </div>
          </div>

          <div className={styles.sectionStack}>
            <div className={styles.sectionBlock}>
              <div className={styles.sectionHeading}>
                <h4>Source selection</h4>
                <p className="muted-note">
                  Choose one experiment for direct export, or switch into candidate-plus-baseline compare mode.
                </p>
              </div>

              <div className={styles.formGrid}>
                <Field label="Experiment" htmlFor="export-experiment">
                  <select
                    id="export-experiment"
                    value={experimentId}
                    onChange={(event) => setExperimentId(event.target.value)}
                  >
                    <option value="">Select an experiment</option>
                    {experiments.map((record) => (
                      <option key={record.experimentId} value={record.experimentId}>
                        {record.publishedAgentId} · {record.datasetName}
                      </option>
                    ))}
                  </select>
                </Field>

                <Field label="Candidate experiment" htmlFor="export-candidate">
                  <select
                    id="export-candidate"
                    value={candidateExperimentId}
                    onChange={(event) => setCandidateExperimentId(event.target.value)}
                  >
                    <option value="">No candidate compare</option>
                    {experiments.map((record) => (
                      <option key={record.experimentId} value={record.experimentId}>
                        {record.publishedAgentId} · {record.datasetName}
                      </option>
                    ))}
                  </select>
                </Field>

                <Field label="Baseline experiment" htmlFor="export-baseline">
                  <select
                    id="export-baseline"
                    value={baselineExperimentId}
                    onChange={(event) => setBaselineExperimentId(event.target.value)}
                    disabled={!candidateExperimentId && !experimentId}
                  >
                    <option value="">No baseline compare</option>
                    {baselineOptions.map((record) => (
                      <option key={record.experimentId} value={record.experimentId}>
                        {record.publishedAgentId} · {record.createdAt}
                      </option>
                    ))}
                  </select>
                </Field>

                <Field label="Format" htmlFor="export-format">
                  <select
                    id="export-format"
                    value={format}
                    onChange={(event) => setFormat(event.target.value as "jsonl" | "parquet")}
                  >
                    <option value="jsonl">jsonl</option>
                    <option value="parquet">parquet</option>
                  </select>
                </Field>
              </div>
            </div>

            <div className={styles.sectionBlock}>
              <div className={styles.filterHeader}>
                <div className={styles.sectionHeading}>
                  <h4>Row filters</h4>
                  <p className="muted-note">Narrow the export set before creating the offline handoff.</p>
                </div>
                <Button variant="ghost" onClick={handleResetFilters} disabled={!activeFilters.length}>
                  <RotateCcw size={14} /> Reset filters
                </Button>
              </div>

              {activeFilters.length ? (
                <div className={styles.filterSummary}>
                  {activeFilters.map((filter) => (
                    <span key={filter} className={styles.filterChip}>
                      {filter}
                    </span>
                  ))}
                </div>
              ) : null}

              <div className={styles.formGrid}>
                <Field label="Judgement" htmlFor="export-judgement">
                  <select
                    id="export-judgement"
                    value={judgementFilter}
                    onChange={(event) => setJudgementFilter(event.target.value)}
                  >
                    <option value="">All judgements</option>
                    <option value="passed">passed</option>
                    <option value="failed">failed</option>
                    <option value="runtime_error">runtime_error</option>
                    <option value="unscored">unscored</option>
                  </select>
                </Field>

                <Field label="Error code" htmlFor="export-error">
                  <select
                    id="export-error"
                    value={errorCodeFilter}
                    onChange={(event) => setErrorCodeFilter(event.target.value)}
                  >
                    <option value="">All error codes</option>
                    {errorCodeOptions.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </Field>

                <Field label="Slice" htmlFor="export-slice">
                  <select id="export-slice" value={sliceFilter} onChange={(event) => setSliceFilter(event.target.value)}>
                    <option value="">All slices</option>
                    {sliceOptions.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </Field>

                <Field label="Tag" htmlFor="export-tag">
                  <select id="export-tag" value={tagFilter} onChange={(event) => setTagFilter(event.target.value)}>
                    <option value="">All tags</option>
                    {tagOptions.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </Field>

                <Field label="Compare outcome" htmlFor="export-compare">
                  <select
                    id="export-compare"
                    value={compareOutcomeFilter}
                    onChange={(event) => setCompareOutcomeFilter(event.target.value)}
                    disabled={!candidateExperimentId || !baselineExperimentId}
                  >
                    <option value="">All compare outcomes</option>
                    <option value="improved">improved</option>
                    <option value="regressed">regressed</option>
                    <option value="unchanged_pass">unchanged_pass</option>
                    <option value="unchanged_fail">unchanged_fail</option>
                    <option value="candidate_only">candidate_only</option>
                    <option value="baseline_only">baseline_only</option>
                  </select>
                </Field>

                <Field label="Curation status" htmlFor="export-curation">
                  <select
                    id="export-curation"
                    value={curationFilter}
                    onChange={(event) => setCurationFilter(event.target.value)}
                  >
                    <option value="">All curation states</option>
                    <option value="include">include</option>
                    <option value="review">review</option>
                    <option value="exclude">exclude</option>
                  </select>
                </Field>

                <Field label="Eligibility" htmlFor="export-eligible">
                  <label className="muted-note" htmlFor="export-eligible">
                    <input
                      id="export-eligible"
                      type="checkbox"
                      checked={exportEligibleOnly}
                      onChange={(event) => setExportEligibleOnly(event.target.checked)}
                    />{" "}
                    only include export-eligible rows
                  </label>
                </Field>
              </div>
            </div>
          </div>

          <div className={styles.handoffLine}>
            <span>
              Mode <strong>{candidateExperimentId ? "compare" : "single experiment"}</strong>
            </span>
            <span>
              Source{" "}
              <strong>
                {sourceExperiment
                  ? `${sourceExperiment.publishedAgentId} on ${sourceExperiment.datasetName}`
                  : "not selected"}
              </strong>
            </span>
            <span>
              Preview <strong>{previewRows.length}</strong> of {runs.length || 0}
            </span>
            <span>
              Review <strong>{previewReviewCount}</strong> rows
            </span>
          </div>

          <div className={styles.actionRow}>
            <Button onClick={handleCreateExport} disabled={createExportMutation.isPending}>
              <Download size={14} /> {createExportMutation.isPending ? "Creating..." : "Create export"}
            </Button>
            <p className={styles.actionNote}>The export uses the current source selection and row filters.</p>
          </div>
        </Panel>

        <Panel tone="plain">
          <div className="surface-header">
            <div>
              <p className="surface-kicker">Export history</p>
              <h3 className="panel-title">Previously generated offline files</h3>
              <p className="muted-note">
                Each export records the source experiment and the filter summary used to produce it.
              </p>
            </div>
          </div>

          {exportsQuery.isPending ? <Notice>Loading export history...</Notice> : null}
          {exportsQuery.isError ? <Notice>Export history is temporarily unavailable.</Notice> : null}

          <TableShell plain>
            <table className={styles.historyTable}>
              <thead>
                <tr>
                  <th>Export</th>
                  <th>Source</th>
                  <th>Rows</th>
                  <th>Filters</th>
                  <th>Download</th>
                </tr>
              </thead>
              <tbody>
                {(exportsQuery.data ?? []).map((record) => (
                  <tr key={record.exportId}>
                    <td>
                      <div className={styles.historyMeta}>
                        <strong className="mono">{record.exportId}</strong>
                        <span className="muted-note">{formatTimestamp(record.createdAt)}</span>
                        <span className="muted-note">{formatBytes(record.sizeBytes)}</span>
                      </div>
                    </td>
                    <td>
                      <div className={styles.historyMeta}>
                        <span className="muted-note">experiment {record.sourceExperimentId || "-"}</span>
                        {record.candidateExperimentId ? (
                          <span className="muted-note">candidate {record.candidateExperimentId}</span>
                        ) : null}
                        {record.baselineExperimentId ? (
                          <span className="muted-note">baseline {record.baselineExperimentId}</span>
                        ) : null}
                      </div>
                    </td>
                    <td>
                      <div className={styles.historyMeta}>
                        <strong>{record.rowCount}</strong>
                        <span className="muted-note">{record.format.toUpperCase()}</span>
                      </div>
                    </td>
                    <td>
                      <div className={styles.historyFilterList}>
                        {summarizeFilterSummary(record.filtersSummary).map((summary) => (
                          <span key={`${record.exportId}-${summary}`} className={styles.historyFilter}>
                            {summary}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td>
                      <Button href={getExportDownloadUrl(record.exportId)} variant="ghost">
                        Download
                      </Button>
                    </td>
                  </tr>
                ))}
                {!exportsQuery.isPending && !(exportsQuery.data ?? []).length ? (
                  <tr>
                    <td colSpan={5}>
                      <Notice>No exports created yet.</Notice>
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </TableShell>
        </Panel>
      </div>
    </section>
  );
}
