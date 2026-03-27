"use client";

import { ArrowUpRight, Radar } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useAgentsQuery } from "@/src/entities/agent/query";
import { useDatasetsQuery } from "@/src/entities/dataset/query";
import type { EvalJobRecord } from "@/src/entities/eval/model";
import { useCreateEvalJobMutation, useEvalJobsQuery, useEvalSamplesQuery } from "@/src/entities/eval/query";
import { ArtifactExportActions } from "@/src/features/artifact-export/ArtifactExportActions";
import { Button } from "@/src/shared/ui/Button";
import { Field } from "@/src/shared/ui/Field";
import { MetricCard } from "@/src/shared/ui/MetricCard";
import { Notice } from "@/src/shared/ui/Notice";
import { Panel } from "@/src/shared/ui/Panel";
import { StatusPill } from "@/src/shared/ui/StatusPill";
import { TableShell } from "@/src/shared/ui/TableShell";
import styles from "./EvalsWorkspace.module.css";

type Props = {
  initialAgentId?: string;
  initialDataset?: string;
  initialJobId?: string;
};

function dedupeStrings(values: string[]) {
  return Array.from(new Set(values));
}

function parseTags(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function toneForStatus(status: "queued" | "running" | "completed" | "failed") {
  if (status === "completed") {
    return "success";
  }
  if (status === "failed") {
    return "error";
  }
  return "warn";
}

function toneForJudgement(judgement: "passed" | "failed" | "unscored" | "runtime_error") {
  if (judgement === "passed") {
    return "success";
  }
  if (judgement === "failed" || judgement === "runtime_error") {
    return "error";
  }
  return "warn";
}

export default function EvalsWorkspace({
  initialAgentId = "",
  initialDataset = "",
  initialJobId = ""
}: Props) {
  const agentsQuery = useAgentsQuery();
  const datasetsQuery = useDatasetsQuery();
  const evalJobsQuery = useEvalJobsQuery();
  const createEvalJobMutation = useCreateEvalJobMutation();
  const [agentId, setAgentId] = useState(initialAgentId);
  const [dataset, setDataset] = useState(initialDataset);
  const [project, setProject] = useState("evals");
  const [scoringMode, setScoringMode] = useState<"exact_match" | "contains">("exact_match");
  const [tagsText, setTagsText] = useState("");
  const [selectedJobId, setSelectedJobId] = useState(initialJobId);
  const [selectedFailureRunIds, setSelectedFailureRunIds] = useState<string[]>([]);
  const [createdJob, setCreatedJob] = useState<EvalJobRecord | null>(null);
  const [actionMessage, setActionMessage] = useState("");

  const agents = useMemo(() => agentsQuery.data ?? [], [agentsQuery.data]);
  const datasets = useMemo(() => datasetsQuery.data ?? [], [datasetsQuery.data]);
  const evalJobs = useMemo(() => evalJobsQuery.data ?? [], [evalJobsQuery.data]);
  const selectedJob =
    evalJobs.find((job) => job.evalJobId === selectedJobId) ??
    (createdJob?.evalJobId === selectedJobId ? createdJob : null) ??
    (selectedJobId ? null : (evalJobs[0] ?? null));
  const evalSamplesQuery = useEvalSamplesQuery(selectedJob?.evalJobId ?? "");
  const samples = useMemo(() => evalSamplesQuery.data ?? [], [evalSamplesQuery.data]);
  const failureSamples = useMemo(
    () =>
      samples
        .filter((sample) => sample.judgement === "failed" || sample.judgement === "runtime_error"),
    [samples]
  );
  const allFailingRunIds = useMemo(() => dedupeStrings(failureSamples.map((sample) => sample.runId)), [failureSamples]);
  const topFailureCodes = selectedJob ? Object.entries(selectedJob.failureDistribution) : [];

  useEffect(() => {
    if (!agentId && agents[0]) {
      setAgentId(agents[0].agentId);
    }
  }, [agentId, agents]);

  useEffect(() => {
    if (!datasets.length) {
      if (dataset) {
        setDataset("");
      }
      return;
    }

    if (!dataset || !datasets.some((item) => item.name === dataset)) {
      setDataset(datasets[0].name);
    }
  }, [dataset, datasets]);

  useEffect(() => {
    if (initialAgentId) {
      setAgentId(initialAgentId);
    }
  }, [initialAgentId]);

  useEffect(() => {
    if (initialDataset) {
      setDataset(initialDataset);
    }
  }, [initialDataset]);

  useEffect(() => {
    if (initialJobId) {
      setSelectedJobId(initialJobId);
    }
  }, [initialJobId]);

  useEffect(() => {
    if (selectedJob?.evalJobId && selectedJob.evalJobId !== selectedJobId) {
      setSelectedJobId(selectedJob.evalJobId);
    }
  }, [selectedJob, selectedJobId]);

  useEffect(() => {
    if (createdJob && evalJobs.some((job) => job.evalJobId === createdJob.evalJobId)) {
      setCreatedJob(null);
    }
  }, [createdJob, evalJobs]);

  useEffect(() => {
    setSelectedFailureRunIds(allFailingRunIds);
  }, [selectedJob?.evalJobId, allFailingRunIds]);

  const toggleFailureRunSelection = (runId: string) => {
    setSelectedFailureRunIds((current) =>
      current.includes(runId) ? current.filter((item) => item !== runId) : [...current, runId]
    );
  };

  const selectedFailureCount = selectedFailureRunIds.length;

  const handleCreateEval = async () => {
    if (!agentId || !dataset) {
      setActionMessage("Select both a published agent and a dataset before creating an eval.");
      return;
    }

    const created = await createEvalJobMutation.mutateAsync({
      agentId,
      dataset,
      project,
      tags: parseTags(tagsText),
      scoringMode
    });
    setCreatedJob(created);
    setSelectedJobId(created.evalJobId);
    setActionMessage(`Created eval job ${created.evalJobId}.`);
  };

  const overallMessage =
    actionMessage ||
    (evalJobsQuery.isPending
      ? "Loading eval jobs..."
      : evalJobsQuery.isError
        ? "Eval workbench is temporarily unavailable."
        : !datasets.length
          ? "No datasets available. Open datasets workspace to import or create one."
        : evalJobs.length
          ? `Loaded ${evalJobs.length} eval jobs.`
          : "No eval jobs yet. Create the first dataset-driven batch run.");

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Dataset evaluation</p>
          <h2 className="section-title">Eval workbench</h2>
          <p className="kicker">
            Launch dataset-driven eval jobs, cluster failures by runtime code, and jump straight into failing runs.
          </p>
          <div className="page-tag-list">
            <span className="page-tag">
              Eval jobs <strong>{evalJobs.length}</strong>
            </span>
            <span className="page-tag">
              Selected status <strong>{selectedJob?.status ?? "idle"}</strong>
            </span>
            <span className="page-tag">
              Failure clusters <strong>{topFailureCodes.length}</strong>
            </span>
          </div>
        </div>
        <div className="page-info-grid">
          <div className="page-info-item">
            <span className="page-info-label">Selected eval</span>
            <span className="page-info-value">{selectedJob?.project ?? "Waiting for selection"}</span>
            <p className="page-info-detail">
              {selectedJob
                ? `${selectedJob.agentId} on ${selectedJob.dataset} · ${selectedJob.passRate.toFixed(2)}% pass rate.`
                : "Use this workspace to batch fan-out dataset rows into linked child runs."}
            </p>
          </div>
          <div className="toolbar">
            <Button href="/datasets" variant="secondary">
              Open datasets workspace
            </Button>
            {selectedJob ? (
              <Button href={`/evals?job=${selectedJob.evalJobId}`} variant="secondary">
                Open selected eval
              </Button>
            ) : null}
            <Button onClick={handleCreateEval} disabled={createEvalJobMutation.isPending}>
              <Radar size={14} /> {createEvalJobMutation.isPending ? "Creating..." : "Create eval job"}
            </Button>
          </div>
        </div>
      </header>

      <div className="summary-strip">
        <MetricCard label="Pass rate" value={selectedJob ? `${selectedJob.passRate.toFixed(2)}%` : "-"} />
        <MetricCard label="Passed" value={selectedJob?.passedCount ?? 0} />
        <MetricCard label="Failed" value={selectedJob?.failedCount ?? 0} />
        <MetricCard label="Runtime errors" value={selectedJob?.runtimeErrorCount ?? 0} />
        <MetricCard label="Unscored" value={selectedJob?.unscoredCount ?? 0} />
        <MetricCard label="Samples" value={selectedJob?.sampleCount ?? 0} />
      </div>

      <Panel tone="strong">
        <div className="surface-header">
          <div>
            <p className="surface-kicker">Launch eval</p>
            <h3 className="panel-title">Create a batch eval from a published agent and dataset</h3>
            <p className="muted-note">Keep scoring deterministic for now and reuse the existing JSONL export path for failures.</p>
          </div>
        </div>

        <div className={styles.formGrid}>
          <Field label="Agent" htmlFor="eval-agent">
            <select id="eval-agent" value={agentId} onChange={(event) => setAgentId(event.target.value)}>
              <option value="">{agents.length ? "Select an agent" : "No published agents"}</option>
              {agents.map((agent) => (
                <option key={agent.agentId} value={agent.agentId}>
                  {agent.name} ({agent.agentId})
                </option>
              ))}
            </select>
          </Field>
          <Field label="Dataset" htmlFor="eval-dataset">
            <select id="eval-dataset" value={dataset} onChange={(event) => setDataset(event.target.value)}>
              <option value="">{datasets.length ? "Select a dataset" : "No datasets. Open datasets workspace"}</option>
              {datasets.map((item) => (
                <option key={item.name} value={item.name}>
                  {item.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Project" htmlFor="eval-project">
            <input id="eval-project" value={project} onChange={(event) => setProject(event.target.value)} />
          </Field>
          <Field label="Scoring mode" htmlFor="eval-scoring-mode">
            <select
              id="eval-scoring-mode"
              value={scoringMode}
              onChange={(event) => setScoringMode(event.target.value as "exact_match" | "contains")}
            >
              <option value="exact_match">exact_match</option>
              <option value="contains">contains</option>
            </select>
          </Field>
          <Field label="Tags" htmlFor="eval-tags">
            <input
              id="eval-tags"
              value={tagsText}
              onChange={(event) => setTagsText(event.target.value)}
              placeholder="nightly, smoke"
            />
          </Field>
        </div>

        {!datasets.length ? (
          <Notice>
            Dataset import now lives in the dedicated datasets workspace.{" "}
            <Button href="/datasets" variant="ghost">
              Open datasets workspace
            </Button>
          </Notice>
        ) : null}

        <div className={styles.formActions}>
          <Button href="/datasets" variant="secondary">
            Open datasets workspace
          </Button>
        </div>

        <Notice>{overallMessage}</Notice>
      </Panel>

      <div className={styles.workspaceGrid}>
        <Panel>
          <div className="surface-header">
            <div>
              <p className="surface-kicker">Jobs</p>
              <h3 className="panel-title">Recent eval jobs</h3>
              <p className="muted-note">Select a batch run to inspect aggregate metrics, clustered failures, and sample-level outcomes.</p>
            </div>
          </div>

          <div className={styles.jobList}>
            {evalJobs.map((job) => (
              <button
                key={job.evalJobId}
                type="button"
                className={`${styles.jobRow} ${selectedJob?.evalJobId === job.evalJobId ? styles.jobRowActive : ""}`}
                onClick={() => setSelectedJobId(job.evalJobId)}
              >
                <div>
                  <strong>{job.project}</strong>
                  <p className="muted-note">
                    {job.agentId} · {job.dataset}
                  </p>
                </div>
                <div className={styles.jobMeta}>
                  <StatusPill tone={toneForStatus(job.status)}>{job.status}</StatusPill>
                  <span className="mono">{job.passRate.toFixed(2)}%</span>
                </div>
              </button>
            ))}
          </div>
        </Panel>

        <Panel>
          <div className="surface-header">
            <div>
              <p className="surface-kicker">Failures</p>
              <h3 className="panel-title">Failure clusters and sample drill-down</h3>
              <p className="muted-note">Use runtime codes to separate infrastructure faults from agent quality regressions.</p>
            </div>
            <div className={styles.failureActions}>
              <div className="toolbar">
                <Button
                  variant="ghost"
                  disabled={!allFailingRunIds.length}
                  onClick={() => setSelectedFailureRunIds(allFailingRunIds)}
                >
                  Select all failures
                </Button>
                <Button
                  variant="ghost"
                  disabled={!selectedFailureCount}
                  onClick={() => setSelectedFailureRunIds([])}
                >
                  Clear selection
                </Button>
              </div>
              <ArtifactExportActions runIds={selectedFailureRunIds} />
            </div>
          </div>

          {selectedJob ? (
            <>
              <div className={styles.failureCodes}>
                {topFailureCodes.length ? (
                  topFailureCodes.map(([code, count]) => (
                    <div key={code} className={styles.failureCode}>
                      <span className="mono">{code}</span>
                      <strong>{count}</strong>
                    </div>
                  ))
                ) : (
                  <Notice>No clustered failures for this eval job.</Notice>
                )}
              </div>
              <p className={styles.selectionSummary}>
                {allFailingRunIds.length
                  ? `${selectedFailureCount} of ${allFailingRunIds.length} failing runs selected for export.`
                  : "No failed runs available to export."}
              </p>
            </>
          ) : (
            <Notice>Select an eval job to inspect clustered failures.</Notice>
          )}

          <TableShell plain>
            <table className={styles.samplesTable}>
              <thead>
                <tr>
                  <th>Select</th>
                  <th>Sample</th>
                  <th>Judgement</th>
                  <th>Error code</th>
                  <th>Actual</th>
                  <th>Run</th>
                </tr>
              </thead>
              <tbody>
                {samples.map((sample) => (
                  <tr key={sample.datasetSampleId}>
                    <td className={styles.selectorCell}>
                      {sample.judgement === "failed" || sample.judgement === "runtime_error" ? (
                        <input
                          type="checkbox"
                          checked={selectedFailureRunIds.includes(sample.runId)}
                          aria-label={`Select failed run ${sample.runId}`}
                          onChange={() => toggleFailureRunSelection(sample.runId)}
                        />
                      ) : (
                        <span className="muted-note">-</span>
                      )}
                    </td>
                    <td className="mono">{sample.datasetSampleId}</td>
                    <td>
                      <StatusPill tone={toneForJudgement(sample.judgement)}>{sample.judgement}</StatusPill>
                    </td>
                    <td className="mono">{sample.errorCode ?? "-"}</td>
                    <td>
                      <div className={styles.sampleDetail}>
                        <span>{sample.actual ?? "-"}</span>
                        {sample.failureReason ? <span className="muted-note">{sample.failureReason}</span> : null}
                      </div>
                    </td>
                    <td>
                      <Button href={`/runs/${sample.runId}`} variant="ghost">
                        Open run {sample.runId} <ArrowUpRight size={14} />
                      </Button>
                    </td>
                  </tr>
                ))}
                {!samples.length ? (
                  <tr>
                    <td colSpan={6}>
                      <Notice>{selectedJob ? "No sample results yet for this eval job." : "Select an eval job first."}</Notice>
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
