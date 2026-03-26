"use client";

import { useQueryClient } from "@tanstack/react-query";
import type { ChangeEvent } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useExportArtifactMutation } from "@/src/entities/artifact/query";
import { useCreateDatasetMutation, useDatasetsQuery } from "@/src/entities/dataset/query";
import { evalJobQueryOptions, useCreateEvalJobMutation } from "@/src/entities/eval/query";
import type { EvalJob, EvalResult } from "@/src/entities/eval/model";
import { useRunsQuery } from "@/src/entities/run/query";
import { trajectoryQueryOptions } from "@/src/entities/trajectory/query";
import type { TrajectoryStep } from "@/src/entities/trajectory/model";
import { DatasetSelector } from "@/src/features/dataset-selector/DatasetSelector";
import { DatasetUpload } from "@/src/features/dataset-upload/DatasetUpload";
import { EvalResultsTable } from "@/src/features/eval-results-table/EvalResultsTable";
import { EvalRunActions } from "@/src/features/eval-run/EvalRunActions";
import { SampleDrilldown } from "@/src/features/sample-drilldown/SampleDrilldown";
import { Field } from "@/src/shared/ui/Field";
import { MetricCard } from "@/src/shared/ui/MetricCard";
import { Panel } from "@/src/shared/ui/Panel";
import { getEvalTotals, getRunEvalSummaries, getVisibleEvalRows } from "./selectors";

const EVAL_JOB_POLL_INTERVAL_MS = 500;

type ParsedDatasetRow = {
  sampleId: string;
  input: string;
  expected?: string | null;
  tags?: string[];
};

function sleep(milliseconds: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}

function parseDatasetJsonl(text: string): ParsedDatasetRow[] {
  const seenSampleIds = new Set<string>();

  return text
    .split("\n")
    .map((line, index) => ({ line: line.trim(), index }))
    .filter((item) => item.line)
    .map(({ line, index }) => {
      let parsed: { sample_id?: string; input?: string; expected?: string; tags?: string[] };

      try {
        parsed = JSON.parse(line) as { sample_id?: string; input?: string; expected?: string; tags?: string[] };
      } catch {
        throw new Error(`Line ${index + 1} is not valid JSON.`);
      }

      const sampleId = parsed.sample_id?.trim() || `sample-${index + 1}`;
      const input = parsed.input?.trim();

      if (!input) {
        throw new Error(`Line ${index + 1} is missing a non-empty input field.`);
      }

      if (seenSampleIds.has(sampleId)) {
        throw new Error(`Duplicate sample_id '${sampleId}' at line ${index + 1}.`);
      }

      seenSampleIds.add(sampleId);

      return {
        sampleId,
        input,
        expected: parsed.expected ?? null,
        tags: parsed.tags ?? []
      };
    });
}

function getEvalJobStatusMessage(job: EvalJob) {
  if (job.status === "failed") {
    return job.failureReason
      ? `Eval job ${job.jobId} finished with status failed: ${job.failureReason}`
      : `Eval job ${job.jobId} finished with status failed`;
  }

  return `Eval job ${job.jobId} finished with status ${job.status}`;
}

type Props = {
  initialRunIds?: string[];
  initialDataset?: string;
};

function isSameSelection(current: string[], next: string[]) {
  return current.length === next.length && current.every((item, index) => item === next[index]);
}

export default function EvalWorkspace({ initialRunIds = [], initialDataset }: Props) {
  const queryClient = useQueryClient();
  const datasetsQuery = useDatasetsQuery();
  const runsQuery = useRunsQuery();
  const createDatasetMutation = useCreateDatasetMutation();
  const createEvalJobMutation = useCreateEvalJobMutation();
  const exportArtifactMutation = useExportArtifactMutation();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [rows, setRows] = useState<EvalResult[]>([]);
  const [dataset, setDataset] = useState(initialDataset ?? "crm-v2");
  const [query, setQuery] = useState("");
  const [selectedSample, setSelectedSample] = useState<EvalResult | null>(null);
  const [selectedRunIds, setSelectedRunIds] = useState<string[]>(initialRunIds);
  const [trajectorySteps, setTrajectorySteps] = useState<TrajectoryStep[]>([]);
  const [isDrilling, setIsDrilling] = useState(false);
  const [failuresOnly, setFailuresOnly] = useState(false);
  const [message, setMessage] = useState("Load datasets and run an eval.");
  const [trajectoryError, setTrajectoryError] = useState("");
  const [uploadSummary, setUploadSummary] = useState("");
  const activeEvalPollRef = useRef(0);
  const datasets = useMemo(() => datasetsQuery.data?.map((item) => item.name) ?? [], [datasetsQuery.data]);
  const runs = runsQuery.data ?? [];
  const runIds = useMemo(() => runs.map((item) => item.runId), [runs]);
  const selectedDataset = useMemo(
    () => datasetsQuery.data?.find((item) => item.name === dataset) ?? null,
    [dataset, datasetsQuery.data]
  );

  const pollEvalJobUntilSettled = async (jobId: string, requestId: number) => {
    while (requestId === activeEvalPollRef.current) {
      const job = await queryClient.fetchQuery(evalJobQueryOptions(jobId));

      if (requestId !== activeEvalPollRef.current) {
        return null;
      }

      setRows(job.results);

      if (job.status === "done" || job.status === "failed") {
        return job;
      }

      setMessage(`Eval job ${job.jobId} is ${job.status}. Waiting for completion...`);
      await sleep(EVAL_JOB_POLL_INTERVAL_MS);
    }

    return null;
  };

  const loadTrajectory = async (row: EvalResult) => {
    setSelectedSample(row);
    setIsDrilling(true);
    setTrajectoryError("");

    try {
      const steps = await queryClient.fetchQuery(trajectoryQueryOptions(row.runId));
      setTrajectorySteps(steps);
      setMessage(`Loaded ${steps.length} trajectory steps for run ${row.runId.slice(0, 8)}.`);
    } catch (error) {
      setTrajectoryError(error instanceof Error ? error.message : "Failed to load trajectory");
      setTrajectorySteps([]);
    } finally {
      setIsDrilling(false);
    }
  };

  const runEval = async () => {
    if (!dataset || selectedRunIds.length === 0) return;
    const requestId = activeEvalPollRef.current + 1;
    activeEvalPollRef.current = requestId;
    setSelectedSample(null);
    setTrajectorySteps([]);
    setTrajectoryError("");
    setRows([]);

    try {
      const job = await createEvalJobMutation.mutateAsync({
        runIds: selectedRunIds,
        dataset,
        evaluators: ["rule", "judge", "tool-correctness"]
      });

      if (requestId !== activeEvalPollRef.current) {
        return;
      }

      setRows(job.results);

      if (job.status === "done" || job.status === "failed") {
        setMessage(getEvalJobStatusMessage(job));
        return;
      }

      setMessage(`Eval job ${job.jobId} is ${job.status}. Waiting for completion...`);
      const completedJob = await pollEvalJobUntilSettled(job.jobId, requestId);

      if (!completedJob || requestId !== activeEvalPollRef.current) {
        return;
      }

      setRows(completedJob.results);
      setMessage(getEvalJobStatusMessage(completedJob));
    } catch (error) {
      if (requestId !== activeEvalPollRef.current) {
        return;
      }

      setRows([]);
      setMessage(error instanceof Error ? error.message : "Failed to run eval job.");
    }
  };

  const exportEvalArtifacts = async (format: "jsonl" | "parquet") => {
    if (selectedRunIds.length === 0) return;
    const artifact = await exportArtifactMutation.mutateAsync({ runIds: selectedRunIds, format });
    setMessage(`Exported ${format.toUpperCase()} artifacts to ${artifact.path}`);
  };

  const handleUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      const datasetRows = parseDatasetJsonl(text);
      const datasetName = file.name.replace(/\.jsonl$/i, "") || `dataset-${Date.now()}`;
      const createdDataset = await createDatasetMutation.mutateAsync({ name: datasetName, rows: datasetRows });
      setDataset(createdDataset.name);
      setUploadSummary(
        `Validated ${datasetRows.length} rows. Preview sample: ${datasetRows
          .slice(0, 2)
          .map((row) => row.sampleId)
          .join(", ")}`
      );
      setMessage(`Uploaded dataset ${createdDataset.name} with ${createdDataset.rows.length} rows.`);
    } catch (error) {
      setUploadSummary("");
      setMessage(error instanceof Error ? error.message : "Failed to validate dataset upload.");
    } finally {
      event.target.value = "";
    }
  };

  useEffect(() => {
    return () => {
      activeEvalPollRef.current += 1;
    };
  }, []);

  useEffect(() => {
    if (!datasets.length) {
      return;
    }

    if (!datasets.includes(dataset)) {
      setDataset(datasets[0]);
    }
  }, [dataset, datasets]);

  useEffect(() => {
    if (!runIds.length) {
      return;
    }

    const validInitialRunIds = initialRunIds.filter((runId) => runIds.includes(runId));
    if (!selectedRunIds.length) {
      const nextSelection = validInitialRunIds.length ? validInitialRunIds : [runIds[0]];
      setSelectedRunIds(nextSelection);
      return;
    }

    const stillValidRunIds = selectedRunIds.filter((runId) => runIds.includes(runId));
    if (!stillValidRunIds.length) {
      const fallbackSelection = validInitialRunIds.length ? validInitialRunIds : [runIds[0]];
      setSelectedRunIds(fallbackSelection);
      return;
    }

    if (!isSameSelection(selectedRunIds, stillValidRunIds)) {
      setSelectedRunIds(stillValidRunIds);
    }
  }, [initialRunIds, runIds, selectedRunIds]);

  const totals = useMemo(() => getEvalTotals(rows), [rows]);
  const failedCount = rows.filter((row) => row.status === "fail").length;
  const visibleRows = useMemo(() => getVisibleEvalRows(rows, query, failuresOnly), [rows, query, failuresOnly]);
  const runSummaries = useMemo(() => getRunEvalSummaries(rows), [rows]);
  const selectedSampleKey = selectedSample ? `${selectedSample.runId}-${selectedSample.sampleId}` : "";

  return (
    <section>
      <div className="topbar">
        <div>
          <h2 className="section-title">Eval bench</h2>
          <p className="kicker">Benchmark runs against datasets and inspect sample-level failures quickly.</p>
        </div>
        <div className="toolbar">
          <DatasetUpload fileInputRef={fileInputRef} onChange={handleUpload} />
          <EvalRunActions onRunEval={runEval} onExport={exportEvalArtifacts} />
        </div>
      </div>

      <div className="metrics">
        <MetricCard label="Success rate" value={`${totals.successRate}%`} />
        <MetricCard label="Tool success" value={`${totals.toolSuccessRate}%`} />
        <MetricCard label="Latency" value={`${totals.latencyMs}ms`} />
        <MetricCard label="Token usage" value={totals.tokenUsage} />
        <MetricCard label="Judge score" value={totals.judgeScore.toFixed(1)} />
      </div>

      <div className="divider" />

      <Panel className="filters">
        <DatasetSelector datasets={datasets} dataset={dataset} onDatasetChange={setDataset} />
        <Field label="Runs to compare" wide>
          <div style={{ display: "grid", gap: 8 }}>
            {runs.map((run) => {
              const checked = selectedRunIds.includes(run.runId);
              const candidateKind = typeof run.projectMetadata?.candidate === "object" ? "candidate" : "";

              return (
                <label
                  key={run.runId}
                  style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer" }}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => {
                      setSelectedRunIds((current) =>
                        checked ? current.filter((runId) => runId !== run.runId) : [...current, run.runId]
                      );
                    }}
                  />
                  <span>
                    {run.runId.slice(0, 8)} · {run.project} · {run.model}
                    {candidateKind ? " · candidate" : ""}
                  </span>
                </label>
              );
            })}
          </div>
        </Field>
        <Field label="Search sample">
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="sample id / run id" />
        </Field>
        <Field label="View">
          <select value={failuresOnly ? "failures" : "all"} onChange={(event) => setFailuresOnly(event.target.value === "failures")}>
            <option value="all">all samples</option>
            <option value="failures">failures only</option>
          </select>
        </Field>
      </Panel>

      <Panel style={{ marginTop: 16 }}>
        <div className="surface-header">
          <div>
            <p className="surface-kicker">Dataset preview</p>
            <h3 className="panel-title">Inspect the active dataset before running eval</h3>
          </div>
        </div>
        <div className="metrics">
          <MetricCard label="Dataset" value={selectedDataset?.name ?? (dataset || "-")} />
          <MetricCard label="Rows" value={selectedDataset?.rows.length ?? 0} />
          <MetricCard
            label="Tagged rows"
            value={selectedDataset?.rows.filter((row) => (row.tags?.length ?? 0) > 0).length ?? 0}
          />
          <MetricCard
            label="Expected labels"
            value={selectedDataset?.rows.filter((row) => Boolean(row.expected)).length ?? 0}
          />
        </div>
        {uploadSummary ? <p className="muted-note">{uploadSummary}</p> : null}
        {selectedDataset?.rows.length ? (
          <div className="table-shell" style={{ marginTop: 12 }}>
            <table>
              <thead>
                <tr>
                  <th>Sample</th>
                  <th>Input</th>
                  <th>Expected</th>
                  <th>Tags</th>
                </tr>
              </thead>
              <tbody>
                {selectedDataset.rows.slice(0, 5).map((row) => (
                  <tr key={row.sampleId}>
                    <td className="mono">{row.sampleId}</td>
                    <td>{row.input}</td>
                    <td>{row.expected ?? "-"}</td>
                    <td>{row.tags?.join(", ") || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted-note">No rows available for preview.</p>
        )}
      </Panel>

      <Panel style={{ marginTop: 16 }}>
        <div className="surface-header">
          <div>
            <p className="surface-kicker">Run summaries</p>
            <h3 className="panel-title">Compare selected runs by pass rate and average score</h3>
          </div>
        </div>
        {runSummaries.length === 0 ? (
          <p className="muted-note">Run an eval job to generate comparison summaries.</p>
        ) : (
          <div className="step-list">
            {runSummaries.map((summary) => (
              <div key={summary.runId} className="step-item">
                <p>
                  {summary.runId.slice(0, 8)} · success {summary.successRate}% · avg score {summary.averageScore}
                </p>
                <p className="muted-note">
                  {summary.passCount} pass · {summary.failCount} fail · {summary.total} samples
                </p>
              </div>
            ))}
          </div>
        )}
      </Panel>

      <div className="run-grid">
        <EvalResultsTable rows={visibleRows} selectedKey={selectedSampleKey} onSelect={loadTrajectory} />
        <SampleDrilldown
          rows={rows}
          failedCount={failedCount}
          selectedSample={selectedSample}
          trajectorySteps={trajectorySteps}
          isDrilling={isDrilling}
          trajectoryError={trajectoryError}
          message={message}
          onSelect={loadTrajectory}
        />
      </div>
    </section>
  );
}
