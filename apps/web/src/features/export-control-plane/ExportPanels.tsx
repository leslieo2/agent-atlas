"use client";

import { Download, RotateCcw } from "lucide-react";
import { getExportDownloadUrl } from "@/src/entities/export/api";
import { COMPARE_OUTCOME_OPTIONS } from "@/src/entities/experiment/compare";
import type { CompareOutcome, CurationStatus, SampleJudgement } from "@/src/shared/api/contract";
import { Button } from "@/src/shared/ui/Button";
import { Field } from "@/src/shared/ui/Field";
import { Notice } from "@/src/shared/ui/Notice";
import { Panel } from "@/src/shared/ui/Panel";
import { TableShell } from "@/src/shared/ui/TableShell";
import { formatBytes, formatTimestamp, summarizeFilterSummary } from "./model";

export function ExportBuilderPanel(props: {
  actionMessage: string;
  activeFilters: string[];
  baselineExperimentId: string;
  baselineOptions: Array<any>;
  candidateExperimentId: string;
  compareOutcomeFilter: CompareOutcome | "";
  createPending: boolean;
  curationFilter: CurationStatus | "";
  errorCodeFilter: string;
  errorCodeOptions: string[];
  experimentId: string;
  experiments: Array<any>;
  exportEligibleOnly: boolean;
  format: "jsonl" | "parquet";
  judgementFilter: SampleJudgement | "";
  latestExportId: string | null;
  onBaselineExperimentIdChange: (value: string) => void;
  onCandidateExperimentIdChange: (value: string) => void;
  onCompareOutcomeFilterChange: (value: CompareOutcome | "") => void;
  onCreateExport: () => void;
  onCurationFilterChange: (value: CurationStatus | "") => void;
  onErrorCodeFilterChange: (value: string) => void;
  onExperimentIdChange: (value: string) => void;
  onExportEligibleOnlyChange: (value: boolean) => void;
  onFormatChange: (value: "jsonl" | "parquet") => void;
  onJudgementFilterChange: (value: SampleJudgement | "") => void;
  onResetFilters: () => void;
  onSliceFilterChange: (value: string) => void;
  onTagFilterChange: (value: string) => void;
  previewReviewCount: number;
  previewRowsCount: number;
  runsCount: number;
  sliceFilter: string;
  sliceOptions: string[];
  sourceExperiment: any;
  styles: Record<string, string>;
  tagFilter: string;
  tagOptions: string[];
}) {
  return (
    <Panel tone="strong">
      <div className="surface-header">
        <div>
          <p className="surface-kicker">Create export</p>
          <h3 className="panel-title">Filter evidence-backed sample outcomes into a training file</h3>
          <p className="muted-note">
            This is the Atlas export handoff surface. First confirm the governed source, then narrow the preview
            rows, then create the offline file that leaves the platform.
          </p>
        </div>
      </div>

      {props.actionMessage ? (
        <Notice>
          {props.actionMessage}{" "}
          {props.latestExportId ? (
            <Button href={getExportDownloadUrl(props.latestExportId)} variant="ghost">
              Download export
            </Button>
          ) : null}
        </Notice>
      ) : null}

      <div className={props.styles.sectionStack}>
        <div className={props.styles.sectionBlock}>
          <div className={props.styles.sectionHeading}>
            <h4>Source selection</h4>
            <p className="muted-note">
              Choose one experiment for direct export, or switch into candidate-plus-baseline compare mode over the
              same evidence model.
            </p>
          </div>

          <div className={props.styles.formGrid}>
            <Field label="Experiment" htmlFor="export-experiment">
              <select id="export-experiment" value={props.experimentId} onChange={(event) => props.onExperimentIdChange(event.target.value)}>
                <option value="">Select an experiment</option>
                {props.experiments.map((record) => (
                  <option key={record.experimentId} value={record.experimentId}>
                    {record.publishedAgentId} · {record.datasetName}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Candidate experiment" htmlFor="export-candidate">
              <select
                id="export-candidate"
                value={props.candidateExperimentId}
                onChange={(event) => props.onCandidateExperimentIdChange(event.target.value)}
              >
                <option value="">No candidate compare</option>
                {props.experiments.map((record) => (
                  <option key={record.experimentId} value={record.experimentId}>
                    {record.publishedAgentId} · {record.datasetName}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Baseline experiment" htmlFor="export-baseline">
              <select
                id="export-baseline"
                value={props.baselineExperimentId}
                onChange={(event) => props.onBaselineExperimentIdChange(event.target.value)}
                disabled={!props.candidateExperimentId && !props.experimentId}
              >
                <option value="">No baseline compare</option>
                {props.baselineOptions.map((record) => (
                  <option key={record.experimentId} value={record.experimentId}>
                    {record.publishedAgentId} · {record.createdAt}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Format" htmlFor="export-format">
              <select id="export-format" value={props.format} onChange={(event) => props.onFormatChange(event.target.value as "jsonl" | "parquet")}>
                <option value="jsonl">jsonl</option>
                <option value="parquet">parquet</option>
              </select>
            </Field>
          </div>
        </div>

        <div className={props.styles.sectionBlock}>
          <div className={props.styles.filterHeader}>
            <div className={props.styles.sectionHeading}>
              <h4>Row filters</h4>
              <p className="muted-note">Narrow the export set before creating the RL-ready handoff.</p>
            </div>
            <Button variant="ghost" onClick={props.onResetFilters} disabled={!props.activeFilters.length}>
              <RotateCcw size={14} /> Reset filters
            </Button>
          </div>

          {props.activeFilters.length ? (
            <div className={props.styles.filterSummary}>
              {props.activeFilters.map((filter) => (
                <span key={filter} className={props.styles.filterChip}>
                  {filter}
                </span>
              ))}
            </div>
          ) : null}

          <div className={props.styles.formGrid}>
            <Field label="Judgement" htmlFor="export-judgement">
              <select
                id="export-judgement"
                value={props.judgementFilter}
                onChange={(event) => props.onJudgementFilterChange(event.target.value as SampleJudgement | "")}
              >
                <option value="">All judgements</option>
                <option value="passed">passed</option>
                <option value="failed">failed</option>
                <option value="runtime_error">runtime_error</option>
                <option value="unscored">unscored</option>
              </select>
            </Field>

            <Field label="Error code" htmlFor="export-error">
              <select id="export-error" value={props.errorCodeFilter} onChange={(event) => props.onErrorCodeFilterChange(event.target.value)}>
                <option value="">All error codes</option>
                {props.errorCodeOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Slice" htmlFor="export-slice">
              <select id="export-slice" value={props.sliceFilter} onChange={(event) => props.onSliceFilterChange(event.target.value)}>
                <option value="">All slices</option>
                {props.sliceOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Tag" htmlFor="export-tag">
              <select id="export-tag" value={props.tagFilter} onChange={(event) => props.onTagFilterChange(event.target.value)}>
                <option value="">All tags</option>
                {props.tagOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Compare outcome" htmlFor="export-compare">
              <select
                id="export-compare"
                value={props.compareOutcomeFilter}
                onChange={(event) => props.onCompareOutcomeFilterChange(event.target.value as CompareOutcome | "")}
                disabled={!props.candidateExperimentId || !props.baselineExperimentId}
              >
                <option value="">All compare outcomes</option>
                {COMPARE_OUTCOME_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Curation status" htmlFor="export-curation">
              <select
                id="export-curation"
                value={props.curationFilter}
                onChange={(event) => props.onCurationFilterChange(event.target.value as CurationStatus | "")}
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
                  checked={props.exportEligibleOnly}
                  onChange={(event) => props.onExportEligibleOnlyChange(event.target.checked)}
                />{" "}
                only include export-eligible rows
              </label>
            </Field>
          </div>
        </div>
      </div>

      <div className={props.styles.handoffLine}>
        <span>
          Mode <strong>{props.candidateExperimentId ? "compare" : "single experiment"}</strong>
        </span>
        <span>
          Source <strong>{props.sourceExperiment ? `${props.sourceExperiment.publishedAgentId} on ${props.sourceExperiment.datasetName}` : "not selected"}</strong>
        </span>
        <span>
          Preview <strong>{props.previewRowsCount}</strong> of {props.runsCount || 0}
        </span>
        <span>
          Review <strong>{props.previewReviewCount}</strong> rows
        </span>
      </div>

      <div className={props.styles.actionRow}>
        <Button onClick={props.onCreateExport} disabled={props.createPending}>
          <Download size={14} /> {props.createPending ? "Creating..." : "Create export"}
        </Button>
        <p className={props.styles.actionNote}>
          {props.sourceExperiment
            ? `Create a ${props.format.toUpperCase()} handoff from the current preview rows for ${props.sourceExperiment.datasetName}.`
            : "Select a source experiment before creating the export handoff."}
        </p>
      </div>
    </Panel>
  );
}

export function ExportHistoryPanel(props: {
  exports: Array<any>;
  isError: boolean;
  isPending: boolean;
  styles: Record<string, string>;
}) {
  return (
    <Panel tone="plain">
      <div className="surface-header">
        <div>
          <p className="surface-kicker">Export history</p>
          <h3 className="panel-title">Previously generated offline files</h3>
          <p className="muted-note">Each export records the source experiment and the filter summary used to produce it.</p>
        </div>
      </div>

      {props.isPending ? <Notice>Loading export history...</Notice> : null}
      {props.isError ? <Notice>Export history is temporarily unavailable.</Notice> : null}

      <TableShell plain>
        <table className={props.styles.historyTable}>
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
            {props.exports.map((record) => (
              <tr key={record.exportId}>
                <td>
                  <div className={props.styles.historyMeta}>
                    <strong className="mono">{record.exportId}</strong>
                    <span className="muted-note">{formatTimestamp(record.createdAt)}</span>
                    <span className="muted-note">{formatBytes(record.sizeBytes)}</span>
                  </div>
                </td>
                <td>
                  <div className={props.styles.historyMeta}>
                    <span className="muted-note">experiment {record.sourceExperimentId || "-"}</span>
                    {record.candidateExperimentId ? <span className="muted-note">candidate {record.candidateExperimentId}</span> : null}
                    {record.baselineExperimentId ? <span className="muted-note">baseline {record.baselineExperimentId}</span> : null}
                  </div>
                </td>
                <td>
                  <div className={props.styles.historyMeta}>
                    <strong>{record.rowCount}</strong>
                    <span className="muted-note">{record.format.toUpperCase()}</span>
                  </div>
                </td>
                <td>
                  <div className={props.styles.historyFilterList}>
                    {summarizeFilterSummary(record.filtersSummary).map((summary) => (
                      <span key={`${record.exportId}-${summary}`} className={props.styles.historyFilter}>
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
            {!props.isPending && !props.exports.length ? (
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
  );
}
