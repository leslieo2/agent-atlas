"use client";

import { ArrowUpRight, Download, Radar, RotateCcw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { AgentRecord } from "@/src/entities/agent/model";
import { getAgentValidationLifecycle } from "@/src/entities/agent/lifecycle";
import { usePublishedAgentsQuery } from "@/src/entities/agent/query";
import { useDatasetsQuery } from "@/src/entities/dataset/query";
import { getExportDownloadUrl } from "@/src/entities/export/api";
import { useCreateExportMutation } from "@/src/entities/export/query";
import type {
  ExperimentCompareSampleRecord,
  ExperimentRecord,
  ExperimentRunRecord
} from "@/src/entities/experiment/model";
import {
  useCancelExperimentMutation,
  useCreateExperimentMutation,
  useExperimentCompareQuery,
  useExperimentRunsQuery,
  useExperimentsQuery,
  usePatchExperimentRunMutation,
  useStartExperimentMutation
} from "@/src/entities/experiment/query";
import { usePoliciesQuery } from "@/src/entities/policy/query";
import type { CompareOutcome, CurationStatus, SampleJudgement, ScoringMode } from "@/src/shared/api/contract";
import { executionProfileSummary } from "@/src/shared/runtime/identity";
import { Button } from "@/src/shared/ui/Button";
import { Field } from "@/src/shared/ui/Field";
import { MetricCard } from "@/src/shared/ui/MetricCard";
import { Notice } from "@/src/shared/ui/Notice";
import { Panel } from "@/src/shared/ui/Panel";
import { StatusPill } from "@/src/shared/ui/StatusPill";
import { TableShell } from "@/src/shared/ui/TableShell";
import styles from "./ExperimentsWorkspace.module.css";

type Props = {
  initialAgentId?: string;
  initialDatasetVersionId?: string;
  initialExperimentId?: string;
};

type ExperimentAgentOption = Pick<AgentRecord, "agentId" | "name" | "executionProfile">;

function canSelectPublishedAgentForExperiment(agent: AgentRecord) {
  const validationLifecycle = getAgentValidationLifecycle(agent);
  return !validationLifecycle.isActive && !validationLifecycle.isBlocking;
}

function parseTags(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function experimentTone(status: string) {
  if (status === "completed") {
    return "success";
  }
  if (status === "failed" || status === "cancelled") {
    return "error";
  }
  return "warn";
}

function judgementTone(judgement?: SampleJudgement | null) {
  if (judgement === "passed") {
    return "success";
  }
  if (judgement === "failed" || judgement === "runtime_error") {
    return "error";
  }
  return "warn";
}

function compareTone(outcome: CompareOutcome) {
  if (outcome === "improved" || outcome === "unchanged_pass") {
    return "success";
  }
  if (outcome === "regressed" || outcome === "baseline_only") {
    return "error";
  }
  return "warn";
}

function uniqueStrings(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value)))).sort();
}

function buildCompareLookup(compareSamples: ExperimentCompareSampleRecord[]) {
  return new Map(compareSamples.map((sample) => [sample.datasetSampleId, sample.compareOutcome]));
}

function matchesRunFilters({
  run,
  judgementFilter,
  errorCodeFilter,
  sliceFilter,
  tagFilter,
  curationFilter,
  compareLookup,
  compareOutcomeFilter
}: {
  run: ExperimentRunRecord;
  judgementFilter: string;
  errorCodeFilter: string;
  sliceFilter: string;
  tagFilter: string;
  curationFilter: string;
  compareLookup: Map<string, CompareOutcome>;
  compareOutcomeFilter: string;
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
  if (curationFilter && run.curationStatus !== curationFilter) {
    return false;
  }
  if (compareOutcomeFilter && compareLookup.get(run.datasetSampleId) !== compareOutcomeFilter) {
    return false;
  }
  return true;
}

function experimentLabel(record: ExperimentRecord) {
  return `${record.name} · ${record.publishedAgentId}`;
}

function experimentNextStep(record: ExperimentRecord | null) {
  if (!record) {
    return "Create an experiment from a governed snapshot to start collecting evidence.";
  }
  if (record.status === "completed") {
    return "Review the evidence summary, compare against a baseline if needed, then curate runs for export.";
  }
  if (record.status === "failed" || record.status === "cancelled") {
    return "Inspect the current evidence summary before deciding whether to retry or compare.";
  }
  return "Let the run finish, then move into compare and curation once evidence is available.";
}

function datasetVersionOptionLabel(datasetName: string, version: string | null | undefined) {
  return `${datasetName} · ${version ? `Version ${version}` : "Unversioned"}`;
}

export default function ExperimentsWorkspace({
  initialAgentId = "",
  initialDatasetVersionId = "",
  initialExperimentId = ""
}: Props) {
  const publishedAgentsQuery = usePublishedAgentsQuery();
  const datasetsQuery = useDatasetsQuery();
  const policiesQuery = usePoliciesQuery();
  const experimentsQuery = useExperimentsQuery();
  const createExperimentMutation = useCreateExperimentMutation();
  const startExperimentMutation = useStartExperimentMutation();
  const cancelExperimentMutation = useCancelExperimentMutation();
  const createExportMutation = useCreateExportMutation();
  const isAgentsLoading = publishedAgentsQuery.isPending;

  const agents = useMemo<ExperimentAgentOption[]>(() => {
    return (publishedAgentsQuery.data ?? [])
      .filter((agent) => canSelectPublishedAgentForExperiment(agent))
      .map((agent) => ({
        agentId: agent.agentId,
        name: agent.name,
        executionProfile: agent.executionProfile
      }));
  }, [publishedAgentsQuery.data]);
  const datasets = useMemo(() => datasetsQuery.data ?? [], [datasetsQuery.data]);
  const policies = useMemo(() => policiesQuery.data ?? [], [policiesQuery.data]);
  const experiments = useMemo(() => experimentsQuery.data ?? [], [experimentsQuery.data]);

  const datasetVersions = useMemo(
    () =>
      datasets.flatMap((dataset) =>
        dataset.versions.map((version) => ({
          ...version,
          datasetLabel: datasetVersionOptionLabel(dataset.name, version.version)
        }))
      ),
    [datasets]
  );

  const [agentId, setAgentId] = useState(initialAgentId);
  const [datasetVersionId, setDatasetVersionId] = useState(initialDatasetVersionId);
  const [model, setModel] = useState("gpt-5.4-mini");
  const [scoringMode, setScoringMode] = useState<ScoringMode>("exact_match");
  const [approvalPolicyId, setApprovalPolicyId] = useState("");
  const [tagsText, setTagsText] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [selectedExperimentId, setSelectedExperimentId] = useState(initialExperimentId);
  const [baselineExperimentId, setBaselineExperimentId] = useState("");
  const [judgementFilter, setJudgementFilter] = useState("");
  const [errorCodeFilter, setErrorCodeFilter] = useState("");
  const [sliceFilter, setSliceFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [curationFilter, setCurationFilter] = useState("");
  const [compareOutcomeFilter, setCompareOutcomeFilter] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [latestExportId, setLatestExportId] = useState<string | null>(null);

  const selectedExperiment = useMemo(
    () => experiments.find((item) => item.experimentId === selectedExperimentId) ?? experiments[0] ?? null,
    [experiments, selectedExperimentId]
  );
  const runsQuery = useExperimentRunsQuery(selectedExperiment?.experimentId ?? "");
  const patchRunMutation = usePatchExperimentRunMutation(selectedExperiment?.experimentId ?? "");
  const compareQuery = useExperimentCompareQuery(baselineExperimentId, selectedExperiment?.experimentId ?? "");
  const runs = useMemo(() => runsQuery.data ?? [], [runsQuery.data]);
  const compareSamples = useMemo(() => compareQuery.data?.samples ?? [], [compareQuery.data?.samples]);
  const compareLookup = useMemo(() => buildCompareLookup(compareSamples), [compareSamples]);

  const baselineOptions = useMemo(
    () =>
      experiments.filter(
        (item) =>
          selectedExperiment &&
          item.datasetVersionId === selectedExperiment.datasetVersionId &&
          item.experimentId !== selectedExperiment.experimentId
      ),
    [experiments, selectedExperiment]
  );
  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.agentId === agentId) ?? null,
    [agentId, agents]
  );

  const filteredRuns = useMemo(
    () =>
      runs.filter((run) =>
        matchesRunFilters({
          run,
          judgementFilter,
          errorCodeFilter,
          sliceFilter,
          tagFilter,
          curationFilter,
          compareLookup,
          compareOutcomeFilter
        })
      ),
    [
      runs,
      judgementFilter,
      errorCodeFilter,
      sliceFilter,
      tagFilter,
      curationFilter,
      compareLookup,
      compareOutcomeFilter
    ]
  );

  const sliceOptions = useMemo(() => uniqueStrings(runs.map((run) => run.slice)), [runs]);
  const tagOptions = useMemo(() => uniqueStrings(runs.flatMap((run) => run.tags)), [runs]);
  const errorCodeOptions = useMemo(() => uniqueStrings(runs.map((run) => run.errorCode)), [runs]);

  useEffect(() => {
    setAgentId(initialAgentId);
  }, [initialAgentId]);

  useEffect(() => {
    setDatasetVersionId(initialDatasetVersionId);
  }, [initialDatasetVersionId]);

  useEffect(() => {
    setSelectedExperimentId(initialExperimentId);
  }, [initialExperimentId]);

  useEffect(() => {
    if (!agents.length) {
      if (!isAgentsLoading && agentId) {
        setAgentId("");
      }
      return;
    }
    if (agentId && agents.some((agent) => agent.agentId === agentId)) {
      return;
    }
    setAgentId(agents[0].agentId);
  }, [agentId, agents, isAgentsLoading]);

  useEffect(() => {
    if (!datasetVersionId && datasetVersions[0]) {
      setDatasetVersionId(datasetVersions[0].datasetVersionId);
    }
  }, [datasetVersionId, datasetVersions]);

  useEffect(() => {
    if (!approvalPolicyId && policies[0]) {
      setApprovalPolicyId(policies[0].approvalPolicyId);
    }
  }, [approvalPolicyId, policies]);

  useEffect(() => {
    if (!baselineOptions.length) {
      setBaselineExperimentId("");
      return;
    }
    if (baselineExperimentId && baselineOptions.some((item) => item.experimentId === baselineExperimentId)) {
      return;
    }
    setBaselineExperimentId(baselineOptions[0]?.experimentId ?? "");
  }, [baselineExperimentId, baselineOptions]);

  const handleCreateExperiment = async () => {
    if (!agentId || !datasetVersionId) {
      setActionMessage("Select a published agent and dataset version before creating an experiment.");
      return;
    }

    const version = datasetVersions.find((item) => item.datasetVersionId === datasetVersionId);
    const created = await createExperimentMutation.mutateAsync({
      name: `${agentId}-${version?.version ?? "latest"}`,
      datasetVersionId,
      publishedAgentId: agentId,
      model,
      scoringMode,
      approvalPolicyId: approvalPolicyId || null,
      systemPrompt,
      promptVersion: version?.version ?? "v1",
      tags: parseTags(tagsText)
    });
    await startExperimentMutation.mutateAsync(created.experimentId);
    setSelectedExperimentId(created.experimentId);
    setActionMessage(`Created and started experiment ${created.experimentId}.`);
  };

  const handlePatchRun = async (
    run: ExperimentRunRecord,
    payload: { curationStatus?: CurationStatus; exportEligible?: boolean }
  ) => {
    await patchRunMutation.mutateAsync({
      runId: run.runId,
      payload: {
        curationStatus: payload.curationStatus ?? run.curationStatus,
        curationNote: run.curationNote ?? null,
        exportEligible: payload.exportEligible ?? run.exportEligible ?? false
      }
    });
  };

  const handleExport = async () => {
    if (!selectedExperiment) {
      setActionMessage("Select an experiment before exporting.");
      return;
    }
    const created = await createExportMutation.mutateAsync({
      experimentId: baselineExperimentId ? null : selectedExperiment.experimentId,
      candidateExperimentId: baselineExperimentId ? selectedExperiment.experimentId : null,
      baselineExperimentId: baselineExperimentId || null,
      datasetSampleIds: filteredRuns.map((run) => run.datasetSampleId),
      judgements: judgementFilter ? [judgementFilter as SampleJudgement] : null,
      errorCodes: errorCodeFilter ? [errorCodeFilter] : null,
      compareOutcomes: compareOutcomeFilter ? [compareOutcomeFilter as CompareOutcome] : null,
      tags: tagFilter ? [tagFilter] : null,
      slices: sliceFilter ? [sliceFilter] : null,
      curationStatuses: curationFilter ? [curationFilter as CurationStatus] : null,
      exportEligible: null,
      format: "jsonl"
    });
    setLatestExportId(created.exportId);
    setActionMessage(`Created export ${created.exportId}.`);
  };

  return (
    <div className={styles.workspace}>
      <div className={styles.hero}>
        <div>
          <p className="page-eyebrow">Experiment control plane</p>
          <h2 className="page-title">Governance to evidence loop</h2>
          <p className="muted-note">
            Atlas turns governed agent snapshots into runs, evidence, and curated exports without promoting provider,
            runner, or credential internals into the product center. Phoenix remains a deeplink for deeper trace inspection.
          </p>
        </div>
        <div className={styles.metricGrid}>
          <MetricCard label="Experiments" value={(experimentsQuery.data ?? []).length} />
          <MetricCard label="Runs in view" value={filteredRuns.length} />
          <MetricCard label="Policies" value={(policiesQuery.data ?? []).length} />
        </div>
      </div>

      <Panel>
        <div className={styles.sectionHeader}>
          <div>
            <p className="surface-kicker">Create experiment</p>
            <h3 className="panel-title">Bind governed snapshot, dataset version, and policy</h3>
            <p className="muted-note">
              Start with one ready governed snapshot, pair it with a dataset version, then let Atlas create the
              evidence loop you will compare and curate.
            </p>
          </div>
        </div>
        {isAgentsLoading ? <Notice>Loading agents...</Notice> : null}
        {!isAgentsLoading && !agents.length ? (
          <Notice>
            No published agents are available yet. Bootstrap or publish a governed snapshot before creating an experiment.
          </Notice>
        ) : null}
        <div className={styles.filtersGrid}>
          <Field label="Published agent" htmlFor="experiment-agent">
            <select id="experiment-agent" value={agentId} onChange={(event) => setAgentId(event.target.value)}>
              {agents.map((agent) => (
                <option key={agent.agentId} value={agent.agentId}>
                  {agent.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Dataset version" htmlFor="experiment-dataset">
            <select
              id="experiment-dataset"
              value={datasetVersionId}
              onChange={(event) => setDatasetVersionId(event.target.value)}
            >
              {datasetVersions.map((version) => (
                <option key={version.datasetVersionId} value={version.datasetVersionId}>
                  {version.datasetLabel}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Model" htmlFor="experiment-model">
            <input id="experiment-model" value={model} onChange={(event) => setModel(event.target.value)} />
          </Field>
          <Field label="Scoring" htmlFor="experiment-scoring">
            <select
              id="experiment-scoring"
              value={scoringMode}
              onChange={(event) => setScoringMode(event.target.value as ScoringMode)}
            >
              <option value="exact_match">exact match</option>
              <option value="contains">contains</option>
            </select>
          </Field>
          <Field label="Approval policy" htmlFor="experiment-policy">
            <select
              id="experiment-policy"
              value={approvalPolicyId}
              onChange={(event) => setApprovalPolicyId(event.target.value)}
            >
              {policies.map((policy) => (
                <option key={policy.approvalPolicyId} value={policy.approvalPolicyId}>
                  {policy.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Tags" htmlFor="experiment-tags">
            <input
              id="experiment-tags"
              placeholder="candidate, nightly"
              value={tagsText}
              onChange={(event) => setTagsText(event.target.value)}
            />
          </Field>
          <Field label="System prompt" htmlFor="experiment-prompt">
            <input
              id="experiment-prompt"
              placeholder="Enforce stable tool usage and concise final answers."
              value={systemPrompt}
              onChange={(event) => setSystemPrompt(event.target.value)}
            />
          </Field>
        </div>
        <p className="muted-note">
          Only ready, governed snapshots appear in this selector. Execution profile is inherited from the published
          snapshot: {executionProfileSummary(selectedAgent?.executionProfile)}. Atlas keeps the same run, evidence, and
          export chain regardless of the underlying execution path.
        </p>
        <div className={styles.actions}>
          <Button onClick={() => void handleCreateExperiment()} disabled={createExperimentMutation.isPending}>
            <Radar size={14} /> {createExperimentMutation.isPending ? "Creating..." : "Create and start"}
          </Button>
          <p className={styles.actionNote}>
            {actionMessage || "Atlas creates the record and immediately starts the run on the current neutral execution path."}
          </p>
        </div>
      </Panel>

      <div className={styles.layout}>
        <Panel>
          <div className={styles.sectionHeader}>
            <div>
              <p className="surface-kicker">Experiments</p>
              <h3 className="panel-title">Select the active experiment</h3>
            </div>
          </div>
          {experimentsQuery.isPending ? <Notice>Loading experiments...</Notice> : null}
          <div className={styles.jobList}>
            {experiments.map((record) => (
              <button
                key={record.experimentId}
                className={styles.jobCard}
                data-active={selectedExperiment?.experimentId === record.experimentId}
                onClick={() => setSelectedExperimentId(record.experimentId)}
              >
                <div className={styles.jobCardHeader}>
                  <strong>{experimentLabel(record)}</strong>
                  <StatusPill tone={experimentTone(record.status)}>{record.status}</StatusPill>
                </div>
                <p className="muted-note">{record.datasetName}</p>
              </button>
            ))}
          </div>
        </Panel>

        <Panel>
          <div className={styles.sectionHeader}>
          <div>
            <p className="surface-kicker">Summary</p>
            <h3 className="panel-title">Selected experiment evidence</h3>
            <p className="muted-note">{experimentNextStep(selectedExperiment)}</p>
          </div>
            {selectedExperiment ? (
              <div className="toolbar">
                <Button
                  variant="secondary"
                  onClick={() => void cancelExperimentMutation.mutateAsync(selectedExperiment.experimentId)}
                  disabled={cancelExperimentMutation.isPending || selectedExperiment.status === "cancelled"}
                >
                  <RotateCcw size={14} /> Cancel
                </Button>
              </div>
            ) : null}
          </div>
          {selectedExperiment ? (
            <>
              <div className={styles.metricGrid}>
                <MetricCard label="Pass rate" value={`${Math.round(selectedExperiment.passRate * 100)}%`} />
                <MetricCard label="Completed" value={selectedExperiment.completedCount} />
                <MetricCard label="Runtime errors" value={selectedExperiment.runtimeErrorCount} />
              </div>
              {selectedExperiment.tracing?.projectUrl ? (
                <Button href={selectedExperiment.tracing.projectUrl} variant="ghost">
                  Open Phoenix deeplink <ArrowUpRight size={14} />
                </Button>
              ) : null}
            </>
          ) : (
            <Notice>No experiments yet.</Notice>
          )}
        </Panel>
      </div>

      <Panel>
        <div className={styles.sectionHeader}>
          <div>
            <p className="surface-kicker">Compare</p>
            <h3 className="panel-title">Baseline vs candidate</h3>
          </div>
        </div>
        <div className={styles.filtersGrid}>
          <Field label="Baseline experiment" htmlFor="experiment-baseline">
            <select
              id="experiment-baseline"
              value={baselineExperimentId}
              onChange={(event) => setBaselineExperimentId(event.target.value)}
            >
              <option value="">No baseline</option>
              {baselineOptions.map((record) => (
                <option key={record.experimentId} value={record.experimentId}>
                  {experimentLabel(record)}
                </option>
              ))}
            </select>
          </Field>
        </div>
        {compareQuery.data ? (
          <div className={styles.metricGrid}>
            {Object.entries(compareQuery.data.distribution).map(([label, count]) => (
              <MetricCard key={label} label={label} value={count} />
            ))}
          </div>
        ) : null}
      </Panel>

      <Panel>
        <div className={styles.sectionHeader}>
          <div>
            <p className="surface-kicker">Runs</p>
            <h3 className="panel-title">Curate sample outcomes before export</h3>
            <p className="muted-note">
              Use compare and curation to decide which evidence-backed rows should move into the next export.
            </p>
          </div>
          <div className="toolbar">
            <Button onClick={() => void handleExport()} disabled={!selectedExperiment || createExportMutation.isPending}>
              <Download size={14} /> {createExportMutation.isPending ? "Exporting..." : "Create export"}
            </Button>
            {latestExportId ? (
              <Button href={getExportDownloadUrl(latestExportId)} variant="ghost">
                Download export
              </Button>
            ) : null}
          </div>
        </div>
        <div className={styles.filtersGrid}>
          <Field label="Judgement" htmlFor="experiment-filter-judgement">
            <select
              id="experiment-filter-judgement"
              value={judgementFilter}
              onChange={(event) => setJudgementFilter(event.target.value)}
            >
              <option value="">All judgements</option>
              <option value="passed">passed</option>
              <option value="failed">failed</option>
              <option value="unscored">unscored</option>
              <option value="runtime_error">runtime_error</option>
            </select>
          </Field>
          <Field label="Error code" htmlFor="experiment-filter-error">
            <select
              id="experiment-filter-error"
              value={errorCodeFilter}
              onChange={(event) => setErrorCodeFilter(event.target.value)}
            >
              <option value="">All errors</option>
              {errorCodeOptions.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Slice" htmlFor="experiment-filter-slice">
            <select id="experiment-filter-slice" value={sliceFilter} onChange={(event) => setSliceFilter(event.target.value)}>
              <option value="">All slices</option>
              {sliceOptions.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Tag" htmlFor="experiment-filter-tag">
            <select id="experiment-filter-tag" value={tagFilter} onChange={(event) => setTagFilter(event.target.value)}>
              <option value="">All tags</option>
              {tagOptions.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Curation" htmlFor="experiment-filter-curation">
            <select
              id="experiment-filter-curation"
              value={curationFilter}
              onChange={(event) => setCurationFilter(event.target.value)}
            >
              <option value="">All curation states</option>
              <option value="include">include</option>
              <option value="review">review</option>
              <option value="exclude">exclude</option>
            </select>
          </Field>
          <Field label="Compare" htmlFor="experiment-filter-compare">
            <select
              id="experiment-filter-compare"
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
        </div>
        {runsQuery.isPending ? <Notice>Loading experiment runs...</Notice> : null}
        <TableShell>
          <table>
            <thead>
              <tr>
                <th>Sample</th>
                <th>Status</th>
                <th>Judgement</th>
                <th>Compare</th>
                <th>Phoenix</th>
                <th>Curation</th>
              </tr>
            </thead>
            <tbody>
              {filteredRuns.map((run) => (
                <tr key={run.runId}>
                  <td>
                    <strong>{run.datasetSampleId}</strong>
                    <p className="muted-note">{run.input}</p>
                  </td>
                  <td>
                    <StatusPill tone={experimentTone(run.runStatus)}>{run.runStatus}</StatusPill>
                  </td>
                  <td>
                    <StatusPill tone={judgementTone(run.judgement)}>{run.judgement ?? "pending"}</StatusPill>
                  </td>
                  <td>
                    {compareLookup.get(run.datasetSampleId) ? (
                      <StatusPill tone={compareTone(compareLookup.get(run.datasetSampleId) as CompareOutcome)}>
                        {compareLookup.get(run.datasetSampleId) as CompareOutcome}
                      </StatusPill>
                    ) : (
                      <span className="muted-note">n/a</span>
                    )}
                  </td>
                  <td>
                    {run.traceUrl ? (
                      <Button href={run.traceUrl} variant="ghost">
                        Open Phoenix <ArrowUpRight size={14} />
                      </Button>
                    ) : (
                      <span className="muted-note">No deeplink</span>
                    )}
                  </td>
                  <td>
                    <div className={styles.curationActions}>
                      <Button
                        variant={run.curationStatus === "include" ? "primary" : "ghost"}
                        onClick={() => void handlePatchRun(run, { curationStatus: "include" })}
                      >
                        Include
                      </Button>
                      <Button
                        variant={run.curationStatus === "review" ? "primary" : "ghost"}
                        onClick={() => void handlePatchRun(run, { curationStatus: "review" })}
                      >
                        Review
                      </Button>
                      <Button
                        variant={run.curationStatus === "exclude" ? "primary" : "ghost"}
                        onClick={() => void handlePatchRun(run, { curationStatus: "exclude" })}
                      >
                        Exclude
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
              {!runsQuery.isPending && !filteredRuns.length ? (
                <tr>
                  <td colSpan={6}>
                    <Notice>No runs match the current filters.</Notice>
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </TableShell>
      </Panel>
    </div>
  );
}
