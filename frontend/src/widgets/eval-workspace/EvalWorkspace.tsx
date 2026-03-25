"use client";

import { useQueryClient } from "@tanstack/react-query";
import type { ChangeEvent } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useExportArtifactMutation } from "@/src/entities/artifact/query";
import { useCreateDatasetMutation, useDatasetsQuery } from "@/src/entities/dataset/query";
import { useCreateEvalJobMutation } from "@/src/entities/eval/query";
import type { EvalResult } from "@/src/entities/eval/model";
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
import { getEvalTotals, getVisibleEvalRows } from "./selectors";

export default function EvalWorkspace() {
  const queryClient = useQueryClient();
  const datasetsQuery = useDatasetsQuery();
  const runsQuery = useRunsQuery();
  const createDatasetMutation = useCreateDatasetMutation();
  const createEvalJobMutation = useCreateEvalJobMutation();
  const exportArtifactMutation = useExportArtifactMutation();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [rows, setRows] = useState<EvalResult[]>([]);
  const [dataset, setDataset] = useState("crm-v2");
  const [query, setQuery] = useState("");
  const [selectedSample, setSelectedSample] = useState<EvalResult | null>(null);
  const [trajectorySteps, setTrajectorySteps] = useState<TrajectoryStep[]>([]);
  const [isDrilling, setIsDrilling] = useState(false);
  const [failuresOnly, setFailuresOnly] = useState(false);
  const [message, setMessage] = useState("Load datasets and run an eval.");
  const [trajectoryError, setTrajectoryError] = useState("");
  const datasets = datasetsQuery.data?.map((item) => item.name) ?? [];
  const runIds = runsQuery.data?.map((item) => item.runId) ?? [];

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
    if (!dataset || !runIds[0]) return;
    const job = await createEvalJobMutation.mutateAsync({
      runIds: [runIds[0]],
      dataset,
      evaluators: ["rule", "judge", "tool-correctness"]
    });
    setRows(job.results);
    setMessage(`Eval job ${job.jobId} finished with status ${job.status}`);
  };

  const exportEvalArtifacts = async (format: "jsonl" | "parquet") => {
    if (!runIds[0]) return;
    const artifact = await exportArtifactMutation.mutateAsync({ runIds: [runIds[0]], format });
    setMessage(`Exported ${format.toUpperCase()} artifacts to ${artifact.path}`);
  };

  const handleUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const text = await file.text();
    const datasetRows = text
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line, index) => {
        const parsed = JSON.parse(line) as { sample_id?: string; input: string; expected?: string; tags?: string[] };
        return {
          sampleId: parsed.sample_id ?? `sample-${index + 1}`,
          input: parsed.input,
          expected: parsed.expected ?? null,
          tags: parsed.tags ?? []
        };
      });

    const datasetName = file.name.replace(/\.jsonl$/i, "") || `dataset-${Date.now()}`;
    const createdDataset = await createDatasetMutation.mutateAsync({ name: datasetName, rows: datasetRows });
    setDataset(createdDataset.name);
    setMessage(`Uploaded dataset ${createdDataset.name} with ${createdDataset.rows.length} rows.`);
    event.target.value = "";
  };

  useEffect(() => {
    if (!datasets.length) {
      return;
    }

    if (!datasets.includes(dataset)) {
      setDataset(datasets[0]);
    }
  }, [dataset, datasets]);

  const totals = useMemo(() => getEvalTotals(rows), [rows]);
  const failedCount = rows.filter((row) => row.status === "fail").length;
  const visibleRows = useMemo(() => getVisibleEvalRows(rows, query, failuresOnly), [rows, query, failuresOnly]);

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

      <div className="run-grid">
        <EvalResultsTable rows={visibleRows} selectedSampleId={selectedSample?.sampleId} onSelect={loadTrajectory} />
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
