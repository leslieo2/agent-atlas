"use client";

import { ArrowUpRight, Download, Radar } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useAgentsQuery } from "@/src/entities/agent/query";
import { useDatasetsQuery } from "@/src/entities/dataset/query";
import { getExportDownloadUrl } from "@/src/entities/export/api";
import { useCreateExportMutation } from "@/src/entities/export/query";
import type { EvalJobRecord, EvalSampleRecord } from "@/src/entities/eval/model";
import {
  useCreateEvalJobMutation,
  useEvalCompareQuery,
  useEvalJobsQuery,
  useEvalSamplesQuery,
  usePatchEvalSampleMutation
} from "@/src/entities/eval/query";
import type {
  CompareOutcome,
  CurationStatus,
  SampleJudgement,
  ScoringMode
} from "@/src/shared/api/contract";
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

function toneForJudgement(judgement: SampleJudgement) {
  if (judgement === "passed") {
    return "success";
  }
  if (judgement === "failed" || judgement === "runtime_error") {
    return "error";
  }
  return "warn";
}

function toneForCompare(outcome: CompareOutcome) {
  if (outcome === "improved" || outcome === "unchanged_pass") {
    return "success";
  }
  if (outcome === "regressed" || outcome === "baseline_only") {
    return "error";
  }
  return "warn";
}

function curationTone(status: CurationStatus) {
  if (status === "include") {
    return "success";
  }
  if (status === "exclude") {
    return "error";
  }
  return "warn";
}

function buildCompareLookup(
  compareSamples: Array<{
    datasetSampleId: string;
    compareOutcome: CompareOutcome;
  }>
) {
  return new Map(compareSamples.map((sample) => [sample.datasetSampleId, sample.compareOutcome]));
}

function matchesSampleFilters({
  sample,
  judgementFilter,
  errorCodeFilter,
  sliceFilter,
  tagFilter,
  curationFilter,
  compareLookup,
  compareOutcomeFilter
}: {
  sample: EvalSampleRecord;
  judgementFilter: string;
  errorCodeFilter: string;
  sliceFilter: string;
  tagFilter: string;
  curationFilter: string;
  compareLookup: Map<string, CompareOutcome>;
  compareOutcomeFilter: string;
}) {
  if (judgementFilter && sample.judgement !== judgementFilter) {
    return false;
  }
  if (errorCodeFilter && sample.errorCode !== errorCodeFilter) {
    return false;
  }
  if (sliceFilter && sample.slice !== sliceFilter) {
    return false;
  }
  if (tagFilter && !sample.tags.includes(tagFilter)) {
    return false;
  }
  if (curationFilter && sample.curationStatus !== curationFilter) {
    return false;
  }
  if (compareOutcomeFilter && compareLookup.get(sample.datasetSampleId) !== compareOutcomeFilter) {
    return false;
  }
  return true;
}

function uniqueStrings(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value)))).sort();
}

function jobTitle(job: EvalJobRecord) {
  return `${job.agentId} on ${job.dataset}`;
}

export default function EvalsWorkspace({ initialAgentId = "", initialDataset = "", initialJobId = "" }: Props) {
  const agentsQuery = useAgentsQuery();
  const datasetsQuery = useDatasetsQuery();
  const evalJobsQuery = useEvalJobsQuery();
  const createEvalJobMutation = useCreateEvalJobMutation();
  const createExportMutation = useCreateExportMutation();

  const [agentId, setAgentId] = useState(initialAgentId);
  const [dataset, setDataset] = useState(initialDataset);
  const [scoringMode, setScoringMode] = useState<ScoringMode>("exact_match");
  const [tagsText, setTagsText] = useState("");
  const [selectedJobId, setSelectedJobId] = useState(initialJobId);
  const [baselineEvalJobId, setBaselineEvalJobId] = useState("");
  const [judgementFilter, setJudgementFilter] = useState("");
  const [errorCodeFilter, setErrorCodeFilter] = useState("");
  const [sliceFilter, setSliceFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [curationFilter, setCurationFilter] = useState("");
  const [compareOutcomeFilter, setCompareOutcomeFilter] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [latestExportId, setLatestExportId] = useState<string | null>(null);

  const agents = useMemo(() => agentsQuery.data ?? [], [agentsQuery.data]);
  const datasets = useMemo(() => datasetsQuery.data ?? [], [datasetsQuery.data]);
  const evalJobs = useMemo(() => evalJobsQuery.data ?? [], [evalJobsQuery.data]);
  const selectedJob = useMemo(
    () => evalJobs.find((job) => job.evalJobId === selectedJobId) ?? evalJobs[0] ?? null,
    [evalJobs, selectedJobId]
  );
  const samplesQuery = useEvalSamplesQuery(selectedJob?.evalJobId ?? "");
  const patchSampleMutation = usePatchEvalSampleMutation(selectedJob?.evalJobId ?? "");
  const compareQuery = useEvalCompareQuery(baselineEvalJobId, selectedJob?.evalJobId ?? "");
  const samples = useMemo(() => samplesQuery.data ?? [], [samplesQuery.data]);
  const compareLookup = useMemo(
    () => buildCompareLookup(compareQuery.data?.samples ?? []),
    [compareQuery.data?.samples]
  );

  const sliceOptions = useMemo(() => uniqueStrings(samples.map((sample) => sample.slice)), [samples]);
  const tagOptions = useMemo(() => uniqueStrings(samples.flatMap((sample) => sample.tags)), [samples]);
  const errorCodeOptions = useMemo(() => uniqueStrings(samples.map((sample) => sample.errorCode)), [samples]);
  const filteredSamples = useMemo(
    () =>
      samples.filter((sample) =>
        matchesSampleFilters({
          sample,
          judgementFilter,
          errorCodeFilter,
          sliceFilter,
          tagFilter,
          curationFilter,
          compareLookup,
          compareOutcomeFilter
        })
      ),
    [samples, judgementFilter, errorCodeFilter, sliceFilter, tagFilter, curationFilter, compareLookup, compareOutcomeFilter]
  );
  const baselineOptions = useMemo(
    () =>
      evalJobs.filter(
        (job) => selectedJob && job.dataset === selectedJob.dataset && job.evalJobId !== selectedJob.evalJobId
      ),
    [evalJobs, selectedJob]
  );

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
    if (initialJobId) {
      setSelectedJobId(initialJobId);
    }
  }, [initialJobId]);

  useEffect(() => {
    if (!baselineOptions.length) {
      setBaselineEvalJobId("");
      return;
    }

    if (baselineEvalJobId && baselineOptions.some((job) => job.evalJobId === baselineEvalJobId)) {
      return;
    }

    setBaselineEvalJobId(baselineOptions[0]?.evalJobId ?? "");
  }, [baselineEvalJobId, baselineOptions]);

  const handleCreateEval = async () => {
    if (!agentId || !dataset) {
      setActionMessage("Select both a published agent and a dataset before creating an eval.");
      return;
    }

    const created = await createEvalJobMutation.mutateAsync({
      agentId,
      dataset,
      scoringMode,
      tags: parseTags(tagsText)
    });
    setSelectedJobId(created.evalJobId);
    setActionMessage(`Created eval job ${created.evalJobId}.`);
  };

  const handlePatchSample = async (
    sample: EvalSampleRecord,
    payload: {
      curationStatus?: CurationStatus;
      exportEligible?: boolean;
    }
  ) => {
    await patchSampleMutation.mutateAsync({
      datasetSampleId: sample.datasetSampleId,
      payload: {
        curationStatus: payload.curationStatus ?? sample.curationStatus,
        curationNote: sample.curationNote ?? null,
        exportEligible: payload.exportEligible ?? sample.exportEligible ?? false
      }
    });
  };

  const handleExportFiltered = async (format: "jsonl" | "parquet") => {
    if (!selectedJob) {
      setActionMessage("Select an eval job before exporting.");
      return;
    }

    if (!filteredSamples.length) {
      setActionMessage("No filtered samples available for export.");
      return;
    }

    const exported = await createExportMutation.mutateAsync({
      evalJobId: baselineEvalJobId ? null : selectedJob.evalJobId,
      baselineEvalJobId: baselineEvalJobId || null,
      candidateEvalJobId: baselineEvalJobId ? selectedJob.evalJobId : null,
      datasetSampleIds: filteredSamples.map((sample) => sample.datasetSampleId),
      judgements: judgementFilter ? [judgementFilter as SampleJudgement] : null,
      errorCodes: errorCodeFilter ? [errorCodeFilter] : null,
      compareOutcomes: compareOutcomeFilter ? [compareOutcomeFilter as CompareOutcome] : null,
      tags: tagFilter ? [tagFilter] : null,
      slices: sliceFilter ? [sliceFilter] : null,
      curationStatuses: curationFilter ? [curationFilter as CurationStatus] : null,
      format
    });

    setLatestExportId(exported.exportId);
    setActionMessage(`Created ${format.toUpperCase()} export ${exported.exportId}.`);
  };

  const overallMessage =
    actionMessage ||
    (evalJobsQuery.isPending
      ? "Loading eval jobs..."
      : evalJobsQuery.isError
        ? "Eval workspace is temporarily unavailable."
        : !datasets.length
          ? "No datasets available. Create a dataset asset first."
          : evalJobs.length
            ? `Loaded ${evalJobs.length} eval jobs.`
            : "No eval jobs yet. Start the first dataset-driven batch run.");

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Batch production</p>
          <h2 className="section-title">Evals</h2>
          <p className="kicker">
            Batch published agents against dataset assets, compare baseline versus candidate behavior, curate the best
            rows, and hand off raw debugging to Phoenix.
          </p>
          <div className="page-tag-list">
            <span className="page-tag">
              Eval jobs <strong>{evalJobs.length}</strong>
            </span>
            <span className="page-tag">
              Filtered samples <strong>{filteredSamples.length}</strong>
            </span>
            <span className="page-tag">
              Compare mode <strong>{baselineEvalJobId ? "on" : "off"}</strong>
            </span>
          </div>
        </div>
        <div className="page-info-grid">
          <div className="page-info-item">
            <span className="page-info-label">Selected eval</span>
            <span className="page-info-value">{selectedJob ? jobTitle(selectedJob) : "Waiting for selection"}</span>
            <p className="page-info-detail">
              {selectedJob
                ? `${selectedJob.passRate.toFixed(2)}% pass rate · ${selectedJob.failedCount} failures · ${selectedJob.runtimeErrorCount} runtime errors`
                : "Eval jobs are the only production path for collecting RL-ready agent data."}
            </p>
          </div>
          <div className="toolbar">
            {selectedJob?.observability?.projectUrl ? (
              <Button href={selectedJob.observability.projectUrl} variant="secondary" target="_blank" rel="noreferrer">
                Open Phoenix job view <ArrowUpRight size={14} />
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
        <MetricCard label="Samples" value={selectedJob?.sampleCount ?? 0} />
      </div>

      {overallMessage ? <Notice>{overallMessage}</Notice> : null}

      <div className={styles.workspaceGrid}>
        <Panel tone="strong">
          <div className="surface-header">
            <div>
              <p className="surface-kicker">Create eval</p>
              <h3 className="panel-title">Launch a dataset-driven batch run</h3>
              <p className="muted-note">
                Pick one published agent and one dataset asset. Every production sample should enter Atlas through this
                path.
              </p>
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
                <option value="">{datasets.length ? "Select a dataset" : "No datasets"}</option>
                {datasets.map((item) => (
                  <option key={item.name} value={item.name}>
                    {item.name}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Scoring mode" htmlFor="eval-scoring">
              <select
                id="eval-scoring"
                value={scoringMode}
                onChange={(event) => setScoringMode(event.target.value as ScoringMode)}
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
                placeholder="regression, export-candidate"
              />
            </Field>
          </div>
        </Panel>

        <Panel tone="plain">
          <div className="surface-header">
            <div>
              <p className="surface-kicker">Eval jobs</p>
              <h3 className="panel-title">Select a completed batch</h3>
              <p className="muted-note">Runs are internal support objects now. Use the job as the top-level unit.</p>
            </div>
          </div>

          {evalJobsQuery.isPending ? <Notice>Loading eval job list...</Notice> : null}
          {evalJobsQuery.isError ? <Notice>Unable to load eval jobs.</Notice> : null}

          <div className={styles.jobList}>
            {evalJobs.map((job) => {
              const isActive = selectedJob?.evalJobId === job.evalJobId;
              return (
                <button
                  key={job.evalJobId}
                  type="button"
                  className={[styles.jobRow, isActive ? styles.jobRowActive : ""].filter(Boolean).join(" ")}
                  onClick={() => setSelectedJobId(job.evalJobId)}
                >
                  <div>
                    <strong>{jobTitle(job)}</strong>
                    <p className="muted-note">{job.project}</p>
                  </div>
                  <div className={styles.jobMeta}>
                    <StatusPill tone={toneForStatus(job.status)}>{job.status}</StatusPill>
                    <span className="muted-note">{job.passRate.toFixed(2)}% pass</span>
                  </div>
                </button>
              );
            })}
          </div>
        </Panel>
      </div>

      <Panel tone="plain">
        <div className="surface-header">
          <div>
            <p className="surface-kicker">Compare and curate</p>
            <h3 className="panel-title">Sample detail for the selected eval job</h3>
            <p className="muted-note">
              Compare a baseline job against the selected candidate, curate sample status, and export only the filtered
              sample set.
            </p>
          </div>
          <div className="toolbar">
            {selectedJob ? (
              <Button
                href={`/exports?eval=${encodeURIComponent(selectedJob.evalJobId)}${
                  baselineEvalJobId
                    ? `&baseline=${encodeURIComponent(baselineEvalJobId)}&candidate=${encodeURIComponent(selectedJob.evalJobId)}`
                    : ""
                }`}
                variant="secondary"
              >
                Open exports <ArrowUpRight size={14} />
              </Button>
            ) : null}
            <Button
              variant="secondary"
              onClick={() => handleExportFiltered("jsonl")}
              disabled={!selectedJob || createExportMutation.isPending}
            >
              <Download size={14} /> Export JSONL
            </Button>
            <Button onClick={() => handleExportFiltered("parquet")} disabled={!selectedJob || createExportMutation.isPending}>
              <Download size={14} /> Export Parquet
            </Button>
          </div>
        </div>

        <div className={styles.formGrid}>
          <Field label="Baseline job" htmlFor="eval-baseline">
            <select
              id="eval-baseline"
              value={baselineEvalJobId}
              onChange={(event) => setBaselineEvalJobId(event.target.value)}
              disabled={!selectedJob}
            >
              <option value="">No compare</option>
              {baselineOptions.map((job) => (
                <option key={job.evalJobId} value={job.evalJobId}>
                  {job.agentId} · {job.createdAt}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Judgement" htmlFor="eval-filter-judgement">
            <select
              id="eval-filter-judgement"
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
          <Field label="Error code" htmlFor="eval-filter-error">
            <select id="eval-filter-error" value={errorCodeFilter} onChange={(event) => setErrorCodeFilter(event.target.value)}>
              <option value="">All error codes</option>
              {errorCodeOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Slice" htmlFor="eval-filter-slice">
            <select id="eval-filter-slice" value={sliceFilter} onChange={(event) => setSliceFilter(event.target.value)}>
              <option value="">All slices</option>
              {sliceOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Tag" htmlFor="eval-filter-tag">
            <select id="eval-filter-tag" value={tagFilter} onChange={(event) => setTagFilter(event.target.value)}>
              <option value="">All tags</option>
              {tagOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Curation" htmlFor="eval-filter-curation">
            <select id="eval-filter-curation" value={curationFilter} onChange={(event) => setCurationFilter(event.target.value)}>
              <option value="">All curation states</option>
              <option value="include">include</option>
              <option value="review">review</option>
              <option value="exclude">exclude</option>
            </select>
          </Field>
          <Field label="Compare outcome" htmlFor="eval-filter-compare">
            <select
              id="eval-filter-compare"
              value={compareOutcomeFilter}
              onChange={(event) => setCompareOutcomeFilter(event.target.value)}
              disabled={!baselineEvalJobId}
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
        </div>

        {baselineEvalJobId && compareQuery.data ? (
          <div className={styles.compareSummary}>
            {Object.entries(compareQuery.data.distribution).map(([outcome, count]) => (
              <div key={outcome} className={styles.compareCard}>
                <span className="muted-note">{outcome}</span>
                <strong>{count}</strong>
              </div>
            ))}
          </div>
        ) : null}

        {latestExportId ? (
          <Notice>
            Latest export ready.{" "}
            <Button href={getExportDownloadUrl(latestExportId)} variant="ghost">
              Download export
            </Button>
          </Notice>
        ) : null}

        {samplesQuery.isPending ? <Notice>Loading sample results...</Notice> : null}
        {samplesQuery.isError ? <Notice>Unable to load sample results for the selected eval.</Notice> : null}

        <TableShell plain>
          <table className={styles.samplesTable}>
            <thead>
              <tr>
                <th>Sample</th>
                <th>Outcome</th>
                <th>Compare</th>
                <th>Details</th>
                <th>Provenance</th>
                <th>Curation</th>
              </tr>
            </thead>
            <tbody>
              {filteredSamples.map((sample) => {
                const compareOutcome = compareLookup.get(sample.datasetSampleId) ?? null;
                return (
                  <tr key={`${sample.evalJobId}-${sample.datasetSampleId}`}>
                    <td>
                      <div className={styles.sampleDetail}>
                        <strong>{sample.datasetSampleId}</strong>
                        <span className="muted-note">{sample.input}</span>
                        <span className="muted-note">
                          {(sample.slice || "no slice") + " · " + (sample.source || "unknown source")}
                        </span>
                      </div>
                    </td>
                    <td>
                      <div className={styles.statusStack}>
                        <StatusPill tone={toneForJudgement(sample.judgement)}>{sample.judgement}</StatusPill>
                        <StatusPill tone={curationTone(sample.curationStatus)}>{sample.curationStatus}</StatusPill>
                      </div>
                    </td>
                    <td>
                      {compareOutcome ? (
                        <StatusPill tone={toneForCompare(compareOutcome)}>{compareOutcome}</StatusPill>
                      ) : (
                        <span className="muted-note">Not compared</span>
                      )}
                    </td>
                    <td>
                      <div className={styles.sampleDetail}>
                        <span>{sample.errorCode || sample.failureReason || "-"}</span>
                        <span className="muted-note">{sample.actual || sample.errorMessage || "No model output."}</span>
                        {sample.tags.length ? <span className="muted-note">{sample.tags.join(", ")}</span> : null}
                        {sample.phoenixTraceUrl ? (
                          <Button href={sample.phoenixTraceUrl} variant="ghost" target="_blank" rel="noreferrer">
                            Open Phoenix <ArrowUpRight size={14} />
                          </Button>
                        ) : null}
                      </div>
                    </td>
                    <td>
                      <div className={styles.sampleDetail}>
                        <span className="muted-note">{sample.runnerBackend || "runner unknown"}</span>
                        <span className="muted-note mono">{sample.artifactRef || sample.imageRef || "-"}</span>
                        <span className="muted-note">
                          {sample.toolCalls ?? 0} tool calls · {sample.latencyMs ?? 0} ms
                        </span>
                      </div>
                    </td>
                    <td>
                      <div className={styles.curationActions}>
                        <div className={styles.actionButtons}>
                          <Button
                            variant="ghost"
                            onClick={() => void handlePatchSample(sample, { curationStatus: "include" })}
                            disabled={patchSampleMutation.isPending}
                          >
                            Include
                          </Button>
                          <Button
                            variant="ghost"
                            onClick={() => void handlePatchSample(sample, { curationStatus: "review" })}
                            disabled={patchSampleMutation.isPending}
                          >
                            Review
                          </Button>
                          <Button
                            variant="ghost"
                            onClick={() => void handlePatchSample(sample, { curationStatus: "exclude" })}
                            disabled={patchSampleMutation.isPending}
                          >
                            Exclude
                          </Button>
                        </div>
                        <label className="muted-note">
                          <input
                            type="checkbox"
                            checked={sample.exportEligible !== false}
                            onChange={(event) =>
                              void handlePatchSample(sample, {
                                exportEligible: event.target.checked
                              })
                            }
                            disabled={patchSampleMutation.isPending}
                          />{" "}
                          export eligible
                        </label>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {!filteredSamples.length ? (
                <tr>
                  <td colSpan={6}>
                    <Notice>No samples match the current filters.</Notice>
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </TableShell>
      </Panel>
    </section>
  );
}
