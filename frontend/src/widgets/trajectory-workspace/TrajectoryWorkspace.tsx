"use client";

import { ArrowLeft, RefreshCcw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { exportArtifact } from "@/src/entities/artifact/api";
import { listRuns } from "@/src/entities/run/api";
import type { RunRecord } from "@/src/entities/run/model";
import { getTrajectory } from "@/src/entities/trajectory/api";
import type { TrajectoryStep } from "@/src/entities/trajectory/model";
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
  getTrajectoryMetrics
} from "./selectors";

type Props = {
  runId?: string;
};

export default function TrajectoryWorkspace({ runId }: Props = {}) {
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [selectedRun, setSelectedRun] = useState(runId ?? "");
  const [steps, setSteps] = useState<TrajectoryStep[]>([]);
  const [message, setMessage] = useState("Loading trajectory...");
  const [diffSummary, setDiffSummary] = useState("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [focusedStepId, setFocusedStepId] = useState("");

  useEffect(() => {
    if (runId) {
      setSelectedRun(runId);
    }
  }, [runId]);

  useEffect(() => {
    listRuns()
      .then((data) => {
        setRuns(data);
        if (!runId && data[0]) {
          setSelectedRun(data[0].runId);
        }
      })
      .catch((error) => setMessage(`Failed to load runs: ${error.message}`));
  }, [runId]);

  useEffect(() => {
    if (!selectedRun) return;
    getTrajectory(selectedRun)
      .then((data) => {
        setSteps(data);
        setExpanded(Object.fromEntries(data.map((step, index) => [step.id, index === 0])));
        setFocusedStepId(data[0]?.id ?? "");
        setMessage(data.length ? `Loaded ${data.length} steps.` : "No trajectory found.");
      })
      .catch((error) => setMessage(`Failed to load trajectory: ${error.message}`));
  }, [selectedRun]);

  const selectedRunRecord = runs.find((run) => run.runId === selectedRun);
  const focusedStep = steps.find((step) => step.id === focusedStepId) ?? steps[0] ?? null;
  const nodes = useMemo(() => buildTrajectoryNodes(steps, focusedStepId), [focusedStepId, steps]);
  const edges = useMemo(() => buildTrajectoryEdges(steps), [steps]);
  const metrics = useMemo(() => getTrajectoryMetrics(steps), [steps]);

  const compareWithPreviousRun = async () => {
    const currentIndex = runs.findIndex((run) => run.runId === selectedRun);
    const previousRun = currentIndex >= 0 ? runs[currentIndex + 1] : undefined;

    if (!previousRun) {
      setDiffSummary("No previous run available for comparison.");
      return;
    }

    const previousSteps = await getTrajectory(previousRun.runId);
    setDiffSummary(compareTrajectories(steps, previousSteps, previousRun.runId));
  };

  const toggleExpanded = (stepId: string) => {
    setFocusedStepId(stepId);
    setExpanded((previous) => ({ ...previous, [stepId]: !previous[stepId] }));
  };

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Run detail</p>
          <h2 className="section-title">Trajectory viewer</h2>
          <p className="kicker">
            Inspect the run graph, review each step, and jump into replay from the current selection.
          </p>
        </div>
        <div className="toolbar">
          <Button href="/runs" variant="secondary">
            <ArrowLeft size={14} /> Back to runs
          </Button>
          <Button
            href={selectedRun ? `/runs/${selectedRun}/replay${focusedStep ? `?stepId=${focusedStep.id}` : ""}` : "/runs"}
          >
            <RefreshCcw size={14} /> Replay selected step
          </Button>
        </div>
      </header>

      <div className="summary-strip">
        <MetricCard label="Run ID" value={selectedRunRecord?.runId ?? (selectedRun || "-")} />
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
              <Button
                variant="ghost"
                onClick={async () => {
                  if (!selectedRun) return;
                  const artifact = await exportArtifact({ runIds: [selectedRun], format: "jsonl" });
                  setMessage(`Trace snapshot exported to ${artifact.path}`);
                }}
              >
                Export trace snapshot
              </Button>
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

