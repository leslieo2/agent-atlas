"use client";

import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Download } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { getArtifactDownloadUrl } from "@/src/entities/artifact/api";
import { useExportArtifactMutation } from "@/src/entities/artifact/query";
import { useRunsQuery } from "@/src/entities/run/query";
import { trajectoryQueryOptions, useTrajectoryQuery } from "@/src/entities/trajectory/query";
import { ArtifactExportFeedback } from "@/src/features/artifact-export/ArtifactExportFeedback";
import { ComparePreviousRunAction } from "@/src/features/trajectory-compare/ComparePreviousRunAction";
import { TrajectoryGraph } from "@/src/features/trajectory-graph/TrajectoryGraph";
import { StepInspector } from "@/src/features/step-inspector/StepInspector";
import { Button } from "@/src/shared/ui/Button";
import { MetricCard } from "@/src/shared/ui/MetricCard";
import { Panel } from "@/src/shared/ui/Panel";
import {
  buildTrajectoryEdges,
  buildTrajectoryNodes,
  compareTrajectories,
  findPreviousComparableRun,
  getTrajectoryMetrics
} from "./selectors";

type Props = {
  runId?: string;
};

type ExportFeedbackState = {
  tone: "success" | "warn" | "error";
  title: string;
  detail?: string;
  downloadHref?: string;
  downloadLabel?: string;
} | null;

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
  const [exportFeedback, setExportFeedback] = useState<ExportFeedbackState>(null);
  const runs = useMemo(() => runsQuery.data ?? [], [runsQuery.data]);
  const trajectoryQuery = useTrajectoryQuery(selectedRun);
  const steps = useMemo(() => trajectoryQuery.data ?? [], [trajectoryQuery.data]);

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
  const nodes = useMemo(() => buildTrajectoryNodes(steps, focusedStepId), [focusedStepId, steps]);
  const edges = useMemo(() => buildTrajectoryEdges(steps), [steps]);
  const metrics = useMemo(() => getTrajectoryMetrics(steps), [steps]);
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
            : "Select a run to inspect.";

  const compareWithPreviousRun = async () => {
    const previousRun = findPreviousComparableRun(runs, selectedRunRecord);

    if (!previousRun) {
      setDiffSummary("No comparable previous run available for comparison.");
      return;
    }

    const previousSteps = await queryClient.fetchQuery(trajectoryQueryOptions(previousRun.runId));
    setDiffSummary(compareTrajectories(steps, previousSteps, previousRun.runId));
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
              <h3 className="panel-title">Select a run and compare it against the previous execution</h3>
              <p className="muted-note">
                Use the graph as the main workspace, then move into the inspector only for step-level detail.
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
              <ComparePreviousRunAction onCompare={compareWithPreviousRun} />
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

          <div className="metrics">
            <MetricCard label="Nodes" value={metrics.toolCalls} />
            <MetricCard label="Failed steps" value={metrics.failed} />
            <MetricCard label="Avg latency" value={`${Math.round(metrics.averageLatency)} ms`} />
            <MetricCard label="Token usage" value={metrics.tokens} />
          </div>

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
