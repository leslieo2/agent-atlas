"use client";

import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Download, ExternalLink } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { getArtifactDownloadUrl } from "@/src/entities/artifact/api";
import { useExportArtifactMutation } from "@/src/entities/artifact/query";
import { useRunsQuery } from "@/src/entities/run/query";
import { useRunTracesQuery } from "@/src/entities/trace/query";
import { buildPlaygroundRerunHref } from "@/src/entities/run/presentation";
import { trajectoryQueryOptions, useTrajectoryQuery } from "@/src/entities/trajectory/query";
import { ArtifactExportFeedback } from "@/src/features/artifact-export/ArtifactExportFeedback";
import { ComparePreviousRunAction } from "@/src/features/trajectory-compare/ComparePreviousRunAction";
import { TrajectoryGraph } from "@/src/features/trajectory-graph/TrajectoryGraph";
import { StepInspector } from "@/src/features/step-inspector/StepInspector";
import { Button } from "@/src/shared/ui/Button";
import { MetricCard } from "@/src/shared/ui/MetricCard";
import { Notice } from "@/src/shared/ui/Notice";
import { Panel } from "@/src/shared/ui/Panel";
import {
  buildTrajectoryEdges,
  buildTrajectoryNodes,
  compareTrajectories,
  getComparableRuns,
  getTrajectoryMetrics
} from "./selectors";

type Props = {
  runId?: string;
};

type SnapshotRuntimeArtifact = {
  buildStatus?: string | null;
  sourceFingerprint?: string | null;
  artifactRef?: string | null;
  imageRef?: string | null;
};

type ExportFeedbackState = {
  tone: "success" | "warn" | "error";
  title: string;
  detail?: string;
  downloadHref?: string;
  downloadLabel?: string;
} | null;

function getSnapshotRuntimeArtifact(snapshot?: Record<string, unknown> | null): SnapshotRuntimeArtifact | null {
  if (!snapshot || typeof snapshot !== "object") {
    return null;
  }

  const raw = snapshot["runtime_artifact"];
  if (!raw || typeof raw !== "object") {
    return null;
  }

  const candidate = raw as Record<string, unknown>;
  return {
    buildStatus: typeof candidate.build_status === "string" ? candidate.build_status : null,
    sourceFingerprint: typeof candidate.source_fingerprint === "string" ? candidate.source_fingerprint : null,
    artifactRef: typeof candidate.artifact_ref === "string" ? candidate.artifact_ref : null,
    imageRef: typeof candidate.image_ref === "string" ? candidate.image_ref : null
  };
}

function hasSameExpandedState(current: Record<string, boolean>, next: Record<string, boolean>) {
  const currentKeys = Object.keys(current);
  const nextKeys = Object.keys(next);

  if (currentKeys.length !== nextKeys.length) {
    return false;
  }

  return nextKeys.every((key) => current[key] === next[key]);
}

export default function TrajectoryWorkspace({ runId }: Props = {}) {
  const queryClient = useQueryClient();
  const runsQuery = useRunsQuery();
  const exportArtifactMutation = useExportArtifactMutation();
  const [selectedRun, setSelectedRun] = useState(runId ?? "");
  const [diffSummary, setDiffSummary] = useState("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [focusedStepId, setFocusedStepId] = useState("");
  const [comparisonRunId, setComparisonRunId] = useState("");
  const [traceStepFilter, setTraceStepFilter] = useState("all");
  const [traceToolFilter, setTraceToolFilter] = useState("all");
  const [exportFeedback, setExportFeedback] = useState<ExportFeedbackState>(null);
  const runs = useMemo(() => runsQuery.data ?? [], [runsQuery.data]);
  const trajectoryQuery = useTrajectoryQuery(selectedRun);
  const tracesQuery = useRunTracesQuery(selectedRun);
  const steps = useMemo(() => trajectoryQuery.data ?? [], [trajectoryQuery.data]);
  const traces = useMemo(() => tracesQuery.data ?? [], [tracesQuery.data]);

  useEffect(() => {
    if (runId) {
      setSelectedRun(runId);
    }
  }, [runId]);

  useEffect(() => {
    if (!runId && !selectedRun && runs[0]) {
      setSelectedRun(runs[0].runId);
    }
  }, [runId, runs, selectedRun]);

  useEffect(() => {
    setExportFeedback(null);
  }, [selectedRun]);

  useEffect(() => {
    setDiffSummary("");
  }, [selectedRun]);

  useEffect(() => {
    setTraceStepFilter("all");
    setTraceToolFilter("all");
  }, [selectedRun]);

  useEffect(() => {
    if (!steps.length) {
      setExpanded((current) => (Object.keys(current).length ? {} : current));
      setFocusedStepId((current) => (current ? "" : current));
      return;
    }

    const nextExpanded = Object.fromEntries(steps.map((step, index) => [step.id, index === 0]));
    setExpanded((current) => (hasSameExpandedState(current, nextExpanded) ? current : nextExpanded));
    setFocusedStepId((current) => (current && steps.some((step) => step.id === current) ? current : steps[0].id));
  }, [steps]);

  const selectedRunRecord = runs.find((run) => run.runId === selectedRun);
  const comparableRuns = useMemo(() => getComparableRuns(runs, selectedRunRecord), [runs, selectedRunRecord]);

  useEffect(() => {
    if (!comparableRuns.length) {
      setComparisonRunId("");
      return;
    }

    setComparisonRunId((current) =>
      comparableRuns.some((run) => run.runId === current) ? current : (comparableRuns[0]?.runId ?? "")
    );
  }, [comparableRuns]);

  const rerunHref = selectedRunRecord ? buildPlaygroundRerunHref(selectedRunRecord) : "/playground";
  const nodes = useMemo(() => buildTrajectoryNodes(steps, focusedStepId), [focusedStepId, steps]);
  const edges = useMemo(() => buildTrajectoryEdges(steps), [steps]);
  const metrics = useMemo(() => getTrajectoryMetrics(steps), [steps]);
  const runtimeArtifact = useMemo(
    () => getSnapshotRuntimeArtifact(selectedRunRecord?.provenance?.publishedAgentSnapshot),
    [selectedRunRecord?.provenance?.publishedAgentSnapshot]
  );
  const message = runsQuery.isError
    ? "Failed to load runs."
    : trajectoryQuery.isPending
      ? "Loading trajectory..."
      : trajectoryQuery.isError
        ? `Failed to load trajectory: ${trajectoryQuery.error instanceof Error ? trajectoryQuery.error.message : "unknown error"}`
        : steps.length
          ? `Loaded ${steps.length} steps.`
          : selectedRun
            ? "No trajectory found."
            : runs.length
              ? "Select a run to inspect."
              : "No runs available yet. Start from Playground to generate a trajectory.";
  const traceStepOptions = useMemo(() => Array.from(new Set(traces.map((trace) => trace.stepType))), [traces]);
  const traceToolOptions = useMemo(
    () =>
      Array.from(
        new Set(traces.map((trace) => trace.toolName).filter((toolName): toolName is string => Boolean(toolName)))
      ),
    [traces]
  );
  const filteredTraces = useMemo(
    () =>
      traces.filter((trace) => {
        if (traceStepFilter !== "all" && trace.stepType !== traceStepFilter) {
          return false;
        }
        if (traceToolFilter !== "all" && trace.toolName !== traceToolFilter) {
          return false;
        }
        return true;
      }),
    [traceStepFilter, traceToolFilter, traces]
  );

  const compareWithSelectedRun = async () => {
    if (!comparisonRunId) {
      setDiffSummary("No comparable runs found in this project / dataset / agent scope.");
      return;
    }

    const comparisonSteps = await queryClient.fetchQuery(trajectoryQueryOptions(comparisonRunId));
    setDiffSummary(compareTrajectories(steps, comparisonSteps, comparisonRunId));
  };

  const toggleExpanded = (stepId: string) => {
    setFocusedStepId(stepId);
    setExpanded((previous) => ({ ...previous, [stepId]: !previous[stepId] }));
  };

  const exportSelectedRun = async () => {
    if (!selectedRun) return;

    setExportFeedback({
      tone: "warn",
      title: "Exporting this run as JSONL...",
      detail: "Preparing artifact and download link."
    });

    try {
      const artifact = await exportArtifactMutation.mutateAsync({ runIds: [selectedRun], format: "jsonl" });
      setExportFeedback({
        tone: "success",
        title: "Run exported as JSONL.",
        detail: `Run ${selectedRun.slice(0, 8)} · ${artifact.sizeBytes} bytes`,
        downloadHref: getArtifactDownloadUrl(artifact.artifactId),
        downloadLabel: "Download JSONL"
      });
    } catch (error) {
      setExportFeedback({
        tone: "error",
        title: "JSONL export failed.",
        detail: error instanceof Error ? error.message : "Try again."
      });
    }
  };

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Run detail</p>
          <h2 className="section-title">Trajectory viewer</h2>
          <p className="kicker">Inspect the run graph, review each step, and inspect registered run metadata.</p>
          <div className="page-tag-list">
            <span className="page-tag">
              Selected run <strong>{selectedRunRecord?.runId ?? (selectedRun || "-")}</strong>
            </span>
            <span className="page-tag">
              Steps <strong>{steps.length}</strong>
            </span>
            <span className="page-tag">
              Status <strong>{selectedRunRecord?.status ?? "pending"}</strong>
            </span>
          </div>
        </div>
        <div className="page-info-grid">
          <div className="page-info-item">
            <span className="page-info-label">Execution context</span>
            <span className="page-info-value">{selectedRunRecord?.project ?? "Waiting for run metadata"}</span>
            <p className="page-info-detail">
              {selectedRunRecord
                ? `${selectedRunRecord.agentType} · ${selectedRunRecord.agentId || "unknown agent"}`
                : "Choose a run to load graph and step details."}
            </p>
          </div>
          <div className="toolbar">
            <Button href="/runs" variant="secondary">
              <ArrowLeft size={14} /> Back to runs
            </Button>
          </div>
        </div>
      </header>

      <div className="summary-strip">
        <MetricCard label="Run ID" value={selectedRunRecord?.runId ?? (selectedRun || "-")} />
        <MetricCard label="Agent ID" value={selectedRunRecord?.agentId ?? "-"} />
        <MetricCard label="Framework" value={selectedRunRecord?.agentType ?? "-"} />
        <MetricCard label="Project" value={selectedRunRecord?.project ?? "-"} />
        <MetricCard label="Failed steps" value={metrics.failed} />
        <MetricCard label="Token usage" value={metrics.tokens} />
      </div>

      <div className="workspace-grid workspace-grid-wide">
        <Panel tone="strong">
          <div className="surface-header">
            <div>
              <p className="surface-kicker">Run context</p>
              <h3 className="panel-title">Select a run and compare it against any scoped execution</h3>
              <p className="muted-note">
                Stay inside the same project, dataset, and agent scope to inspect regressions without leaving detail
                view.
              </p>
            </div>
            <div className="toolbar">
              {!runId ? (
                <select value={selectedRun} onChange={(event) => setSelectedRun(event.target.value)}>
                  {runs.map((run) => (
                    <option key={run.runId} value={run.runId}>
                      {run.runId.slice(0, 8)} · {run.project}
                    </option>
                  ))}
                </select>
              ) : null}
              {selectedRunRecord ? (
                <Button href={rerunHref} variant="secondary">
                  Rerun in Playground
                </Button>
              ) : null}
              <ComparePreviousRunAction
                comparableRuns={comparableRuns}
                selectedRunId={comparisonRunId}
                onSelectedRunIdChange={setComparisonRunId}
                onCompare={compareWithSelectedRun}
              />
              <div className="action-stack action-stack-right">
                <Button
                  variant="ghost"
                  disabled={!selectedRun || exportArtifactMutation.isPending}
                  onClick={exportSelectedRun}
                >
                  <Download size={14} /> {exportArtifactMutation.isPending ? "Exporting..." : "Export Run JSONL"}
                </Button>
                {exportFeedback ? <ArtifactExportFeedback {...exportFeedback} /> : null}
              </div>
            </div>
          </div>
          {selectedRunRecord && comparableRuns.length === 0 ? (
            <Notice>No comparable runs found in this project / dataset / agent scope.</Notice>
          ) : null}
          {!selectedRunRecord && !runsQuery.isPending && !runs.length ? (
            <Notice>No runs available yet. Start from Playground to generate a trajectory.</Notice>
          ) : null}

          <div className="metrics">
            <MetricCard label="Nodes" value={metrics.toolCalls} />
            <MetricCard label="Failed steps" value={metrics.failed} />
            <MetricCard label="Avg latency" value={`${Math.round(metrics.averageLatency)} ms`} />
            <MetricCard label="Token usage" value={metrics.tokens} />
          </div>

          {selectedRunRecord ? (
            <div className="surface" style={{ marginBottom: 18 }}>
              <div className="surface-header">
                <div>
                  <p className="surface-kicker">Run context</p>
                  <h4 className="panel-title">Published snapshot and execution details</h4>
                  <p className="muted-note">
                    Inspect the exact agent handoff, runtime backend, and failure reason before re-running.
                  </p>
                </div>
              </div>
              <div className="metrics">
                <MetricCard label="Resolved model" value={selectedRunRecord.resolvedModel ?? "-"} />
                <MetricCard
                  label="Runner backend"
                  value={selectedRunRecord.runnerBackend ?? selectedRunRecord.provenance?.runnerBackend ?? "-"}
                />
                <MetricCard label="Backend" value={selectedRunRecord.executionBackend ?? "-"} />
                <MetricCard
                  label="Artifact handoff"
                  value={selectedRunRecord.provenance?.artifactRef ?? runtimeArtifact?.artifactRef ?? "-"}
                />
                <MetricCard
                  label="Image handoff"
                  value={
                    selectedRunRecord.imageRef ??
                    selectedRunRecord.provenance?.imageRef ??
                    runtimeArtifact?.imageRef ??
                    "-"
                  }
                />
                <MetricCard label="Container image" value={selectedRunRecord.containerImage ?? "-"} />
                <MetricCard label="Failure code" value={selectedRunRecord.errorCode ?? "-"} />
              </div>
              <Notice className="mono">
                {[
                  `entrypoint: ${selectedRunRecord.entrypoint ?? "-"}`,
                  `runner_backend: ${selectedRunRecord.runnerBackend ?? selectedRunRecord.provenance?.runnerBackend ?? "-"}`,
                  `trace_backend: ${selectedRunRecord.provenance?.traceBackend ?? selectedRunRecord.observability?.backend ?? "-"}`,
                  `artifact_ref: ${selectedRunRecord.provenance?.artifactRef ?? runtimeArtifact?.artifactRef ?? "-"}`,
                  `image_ref: ${selectedRunRecord.imageRef ?? selectedRunRecord.provenance?.imageRef ?? runtimeArtifact?.imageRef ?? "-"}`,
                  `build_status: ${runtimeArtifact?.buildStatus ?? "legacy"}`,
                  `source_fingerprint: ${runtimeArtifact?.sourceFingerprint ?? "legacy"}`,
                  ...(selectedRunRecord.errorMessage ? [`error: ${selectedRunRecord.errorMessage}`] : [])
                ].join("\n")}
              </Notice>
            </div>
          ) : null}

          {selectedRunRecord ? (
            <div className="surface" style={{ marginBottom: 18 }}>
              <div className="surface-header">
                <div>
                  <p className="surface-kicker">Raw traces</p>
                  <h4 className="panel-title">Phoenix-backed raw trace panel</h4>
                  <p className="muted-note">
                    Atlas fetches raw traces through its own API and only deep-links out to Phoenix when available.
                  </p>
                </div>
                <div className="toolbar">
                  <select value={traceStepFilter} onChange={(event) => setTraceStepFilter(event.target.value)}>
                    <option value="all">All step types</option>
                    {traceStepOptions.map((stepType) => (
                      <option key={stepType} value={stepType}>
                        {stepType}
                      </option>
                    ))}
                  </select>
                  <select value={traceToolFilter} onChange={(event) => setTraceToolFilter(event.target.value)}>
                    <option value="all">All tools</option>
                    {traceToolOptions.map((toolName) => (
                      <option key={toolName} value={toolName}>
                        {toolName}
                      </option>
                    ))}
                  </select>
                  {selectedRunRecord.observability?.traceUrl ? (
                    <Button
                      href={selectedRunRecord.observability.traceUrl}
                      variant="secondary"
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open Phoenix trace <ExternalLink size={14} />
                    </Button>
                  ) : null}
                </div>
              </div>
              <div className="metrics">
                <MetricCard
                  label="Trace backend"
                  value={selectedRunRecord.observability?.backend ?? selectedRunRecord.provenance?.traceBackend ?? "-"}
                />
                <MetricCard label="Trace spans" value={traces.length} />
                <MetricCard label="Filtered spans" value={filteredTraces.length} />
                <MetricCard label="Trace ID" value={selectedRunRecord.observability?.traceId ?? "-"} />
              </div>
              {tracesQuery.isPending ? <Notice>Loading raw traces...</Notice> : null}
              {tracesQuery.isError ? (
                <Notice>
                  Failed to load raw traces:{" "}
                  {tracesQuery.error instanceof Error ? tracesQuery.error.message : "unknown error"}
                </Notice>
              ) : null}
              {!tracesQuery.isPending && !tracesQuery.isError && !filteredTraces.length ? (
                <Notice>No raw traces available for the selected filters.</Notice>
              ) : null}
              {filteredTraces.length ? (
                <Notice className="mono">
                  {filteredTraces
                    .map((trace) =>
                      [
                        `[${trace.stepType}] ${trace.spanId}`,
                        `parent=${trace.parentSpanId ?? "-"}`,
                        `tool=${trace.toolName ?? "-"}`,
                        `latency_ms=${trace.latencyMs}`,
                        `tokens=${trace.tokenUsage}`,
                        `backend=${trace.traceBackend ?? selectedRunRecord.observability?.backend ?? "-"}`,
                        `input=${JSON.stringify(trace.input)}`,
                        `output=${JSON.stringify(trace.output)}`
                      ].join(" | ")
                    )
                    .join("\n\n")}
                </Notice>
              ) : null}
            </div>
          ) : null}

          <TrajectoryGraph nodes={nodes} edges={edges} />
        </Panel>

        <StepInspector
          steps={steps}
          focusedStepId={focusedStepId}
          expanded={expanded}
          diffSummary={diffSummary}
          message={message}
          onToggleExpanded={toggleExpanded}
        />
      </div>
    </section>
  );
}
