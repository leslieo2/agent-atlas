"use client";

import { Download } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { getExportDownloadUrl } from "@/src/entities/export/api";
import { useCreateExportMutation, useExportsQuery } from "@/src/entities/export/query";
import { useEvalJobsQuery, useEvalSamplesQuery } from "@/src/entities/eval/query";
import type { CompareOutcome, CurationStatus, SampleJudgement } from "@/src/shared/api/contract";
import { Button } from "@/src/shared/ui/Button";
import { Field } from "@/src/shared/ui/Field";
import { MetricCard } from "@/src/shared/ui/MetricCard";
import { Notice } from "@/src/shared/ui/Notice";
import { Panel } from "@/src/shared/ui/Panel";
import { TableShell } from "@/src/shared/ui/TableShell";
import styles from "./ExportsWorkspace.module.css";

type Props = {
  initialEvalJobId?: string;
  initialBaselineEvalJobId?: string;
  initialCandidateEvalJobId?: string;
};

function uniqueStrings(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value)))).sort();
}

export default function ExportsWorkspace({
  initialEvalJobId = "",
  initialBaselineEvalJobId = "",
  initialCandidateEvalJobId = ""
}: Props) {
  const evalJobsQuery = useEvalJobsQuery();
  const exportsQuery = useExportsQuery();
  const createExportMutation = useCreateExportMutation();

  const [evalJobId, setEvalJobId] = useState(initialEvalJobId);
  const [baselineEvalJobId, setBaselineEvalJobId] = useState(initialBaselineEvalJobId);
  const [candidateEvalJobId, setCandidateEvalJobId] = useState(initialCandidateEvalJobId);
  const [judgementFilter, setJudgementFilter] = useState("");
  const [errorCodeFilter, setErrorCodeFilter] = useState("");
  const [sliceFilter, setSliceFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [compareOutcomeFilter, setCompareOutcomeFilter] = useState("");
  const [curationFilter, setCurationFilter] = useState("");
  const [exportEligibleOnly, setExportEligibleOnly] = useState(true);
  const [format, setFormat] = useState<"jsonl" | "parquet">("jsonl");
  const [actionMessage, setActionMessage] = useState("");

  const evalJobs = useMemo(() => evalJobsQuery.data ?? [], [evalJobsQuery.data]);
  const selectedSourceEvalId = candidateEvalJobId || evalJobId;
  const sourceEvalJob = useMemo(
    () => evalJobs.find((job) => job.evalJobId === selectedSourceEvalId) ?? null,
    [evalJobs, selectedSourceEvalId]
  );
  const selectedSamplesQuery = useEvalSamplesQuery(selectedSourceEvalId);
  const samples = useMemo(() => selectedSamplesQuery.data ?? [], [selectedSamplesQuery.data]);
  const errorCodeOptions = useMemo(() => uniqueStrings(samples.map((sample) => sample.errorCode)), [samples]);
  const sliceOptions = useMemo(() => uniqueStrings(samples.map((sample) => sample.slice)), [samples]);
  const tagOptions = useMemo(() => uniqueStrings(samples.flatMap((sample) => sample.tags)), [samples]);
  const baselineOptions = useMemo(
    () =>
      sourceEvalJob
        ? evalJobs.filter((job) => job.dataset === sourceEvalJob.dataset && job.evalJobId !== sourceEvalJob.evalJobId)
        : [],
    [evalJobs, sourceEvalJob]
  );

  useEffect(() => {
    if (!selectedSourceEvalId && evalJobs[0]) {
      setEvalJobId(evalJobs[0].evalJobId);
    }
  }, [evalJobs, selectedSourceEvalId]);

  useEffect(() => {
    if (candidateEvalJobId) {
      return;
    }

    if (baselineEvalJobId && baselineOptions.some((job) => job.evalJobId === baselineEvalJobId)) {
      return;
    }

    setBaselineEvalJobId("");
  }, [baselineEvalJobId, baselineOptions, candidateEvalJobId]);

  const handleCreateExport = async () => {
    if (!selectedSourceEvalId) {
      setActionMessage("Select an eval source before creating an export.");
      return;
    }

    const exported = await createExportMutation.mutateAsync({
      evalJobId: candidateEvalJobId ? null : evalJobId || null,
      baselineEvalJobId: baselineEvalJobId || null,
      candidateEvalJobId: candidateEvalJobId || null,
      judgements: judgementFilter ? [judgementFilter as SampleJudgement] : null,
      errorCodes: errorCodeFilter ? [errorCodeFilter] : null,
      compareOutcomes: compareOutcomeFilter ? [compareOutcomeFilter as CompareOutcome] : null,
      tags: tagFilter ? [tagFilter] : null,
      slices: sliceFilter ? [sliceFilter] : null,
      curationStatuses: curationFilter ? [curationFilter as CurationStatus] : null,
      exportEligible: exportEligibleOnly,
      format
    });

    setActionMessage(`Created export ${exported.exportId}.`);
  };

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Offline handoff</p>
          <h2 className="section-title">Exports</h2>
          <p className="kicker">
            Convert eval sample results into RL-ready offline files. Export only the samples that survived compare,
            curation, and provenance checks.
          </p>
          <div className="page-tag-list">
            <span className="page-tag">
              Exports <strong>{(exportsQuery.data ?? []).length}</strong>
            </span>
            <span className="page-tag">
              Source dataset <strong>{sourceEvalJob?.dataset ?? "none"}</strong>
            </span>
            <span className="page-tag">
              Source samples <strong>{samples.length}</strong>
            </span>
          </div>
        </div>
        <div className="page-info-grid">
          <div className="page-info-item">
            <span className="page-info-label">Current source</span>
            <span className="page-info-value">{sourceEvalJob ? `${sourceEvalJob.agentId} on ${sourceEvalJob.dataset}` : "Waiting for selection"}</span>
            <p className="page-info-detail">
              {candidateEvalJobId
                ? "Compare-aware export mode is active."
                : "Export rows directly from one eval job or switch into compare-aware mode by providing a candidate eval."}
            </p>
          </div>
        </div>
      </header>

      <div className="summary-strip">
        <MetricCard label="History" value={(exportsQuery.data ?? []).length} />
        <MetricCard label="Rows in source" value={samples.length} />
        <MetricCard label="Candidate mode" value={candidateEvalJobId ? "yes" : "no"} />
        <MetricCard label="Format" value={format.toUpperCase()} />
      </div>

      {actionMessage ? <Notice>{actionMessage}</Notice> : null}

      <div className={styles.workspaceGrid}>
        <Panel tone="strong">
          <div className="surface-header">
            <div>
              <p className="surface-kicker">Create export</p>
              <h3 className="panel-title">Filter eval samples into a training file</h3>
              <p className="muted-note">
                This is the Atlas handoff surface. Phoenix explains failures; Atlas decides what leaves the platform.
              </p>
            </div>
          </div>

          <div className={styles.formGrid}>
            <Field label="Eval job" htmlFor="export-eval">
              <select id="export-eval" value={evalJobId} onChange={(event) => setEvalJobId(event.target.value)}>
                <option value="">Select an eval job</option>
                {evalJobs.map((job) => (
                  <option key={job.evalJobId} value={job.evalJobId}>
                    {job.agentId} · {job.dataset}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Candidate eval" htmlFor="export-candidate">
              <select
                id="export-candidate"
                value={candidateEvalJobId}
                onChange={(event) => setCandidateEvalJobId(event.target.value)}
              >
                <option value="">No candidate compare</option>
                {evalJobs.map((job) => (
                  <option key={job.evalJobId} value={job.evalJobId}>
                    {job.agentId} · {job.dataset}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Baseline eval" htmlFor="export-baseline">
              <select
                id="export-baseline"
                value={baselineEvalJobId}
                onChange={(event) => setBaselineEvalJobId(event.target.value)}
                disabled={!candidateEvalJobId && !evalJobId}
              >
                <option value="">No baseline compare</option>
                {baselineOptions.map((job) => (
                  <option key={job.evalJobId} value={job.evalJobId}>
                    {job.agentId} · {job.createdAt}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Format" htmlFor="export-format">
              <select id="export-format" value={format} onChange={(event) => setFormat(event.target.value as "jsonl" | "parquet")}>
                <option value="jsonl">jsonl</option>
                <option value="parquet">parquet</option>
              </select>
            </Field>

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
              <select id="export-error" value={errorCodeFilter} onChange={(event) => setErrorCodeFilter(event.target.value)}>
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
                only include export-eligible samples
              </label>
            </Field>
          </div>

          <div className="toolbar">
            <Button onClick={handleCreateExport} disabled={createExportMutation.isPending}>
              <Download size={14} /> {createExportMutation.isPending ? "Creating..." : "Create export"}
            </Button>
          </div>
        </Panel>

        <Panel tone="plain">
          <div className="surface-header">
            <div>
              <p className="surface-kicker">Export history</p>
              <h3 className="panel-title">Previously generated offline files</h3>
              <p className="muted-note">Each export records the source eval and the filter summary used to produce it.</p>
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
                        <span className="muted-note">{record.createdAt}</span>
                      </div>
                    </td>
                    <td>
                      <div className={styles.historyMeta}>
                        <span className="muted-note">eval {record.sourceEvalJobId || "-"}</span>
                        {record.candidateEvalJobId ? (
                          <span className="muted-note">candidate {record.candidateEvalJobId}</span>
                        ) : null}
                        {record.baselineEvalJobId ? (
                          <span className="muted-note">baseline {record.baselineEvalJobId}</span>
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
                      <pre className="muted-note mono">{JSON.stringify(record.filtersSummary, null, 2)}</pre>
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
