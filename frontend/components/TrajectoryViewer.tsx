"use client";

import { useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  MarkerType
} from "reactflow";
import "reactflow/dist/style.css";
import { ChevronDown, ChevronUp, Copy } from "lucide-react";
import { exportArtifact, getTrajectory, listRuns, RunRecord, TrajectoryStep } from "@/lib/api";

export default function TrajectoryViewer() {
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [selectedRun, setSelectedRun] = useState("");
  const [steps, setSteps] = useState<TrajectoryStep[]>([]);
  const [message, setMessage] = useState("Loading trajectory...");
  const [diffSummary, setDiffSummary] = useState("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  useEffect(() => {
    listRuns()
      .then((data) => {
        setRuns(data);
        if (data[0]) setSelectedRun(data[0].runId);
      })
      .catch((error) => setMessage(`Failed to load runs: ${error.message}`));
  }, []);

  useEffect(() => {
    if (!selectedRun) return;
    getTrajectory(selectedRun)
      .then((data) => {
        setSteps(data);
        setExpanded(Object.fromEntries(data.map((step, index) => [step.id, index === 0])));
        setMessage(data.length ? `Loaded ${data.length} steps.` : "No trajectory found.");
      })
      .catch((error) => setMessage(`Failed to load trajectory: ${error.message}`));
  }, [selectedRun]);

  const nodes: Node[] = useMemo(
    () =>
      steps.map((step, index) => ({
        id: step.id,
        position: { x: 140 + index * 250, y: 130 },
        data: { label: step.stepType.toUpperCase() },
        type: "default",
        style: {
          borderColor: step.success ? "#6effa6" : "#ff7a87",
          borderWidth: 2,
          width: 130,
          background: "#0d132f",
          color: "#e8ecff",
          textAlign: "center"
        }
      })),
    [steps]
  );

  const edges: Edge[] = useMemo(
    () =>
      steps.slice(0, -1).map((step, index) => ({
        id: `e-${step.id}-${steps[index + 1].id}`,
        source: step.id,
        target: steps[index + 1].id,
        animated: true,
        style: {
          stroke: "#6bc7ff"
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: "#6bc7ff"
        }
      })),
    [steps]
  );

  const metrics = useMemo(
    () => ({
      toolCalls: steps.length,
      failed: steps.filter((s) => !s.success).length,
      averageLatency:
        steps.reduce((acc, curr) => acc + curr.latencyMs, 0) / Math.max(steps.length, 1),
      tokens: steps.reduce((acc, curr) => acc + curr.tokenUsage, 0)
    }),
    [steps]
  );

  const toggleExpanded = (id: string) => setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
  const anyExpanded = Object.values(expanded).some(Boolean);

  const compareWithPreviousRun = async () => {
    const currentIndex = runs.findIndex((run) => run.runId === selectedRun);
    const previousRun = currentIndex >= 0 ? runs[currentIndex + 1] : undefined;
    if (!previousRun) {
      setDiffSummary("No previous run available for comparison.");
      return;
    }

    const previousSteps = await getTrajectory(previousRun.runId);
    const maxLength = Math.max(steps.length, previousSteps.length);
    const lines: string[] = [];

    for (let index = 0; index < maxLength; index += 1) {
      const current = steps[index];
      const previous = previousSteps[index];

      if (!current && previous) {
        lines.push(`Only in previous run: ${previous.id} (${previous.stepType})`);
        continue;
      }
      if (current && !previous) {
        lines.push(`Only in current run: ${current.id} (${current.stepType})`);
        continue;
      }
      if (!current || !previous) continue;

      const changes: string[] = [];
      if (current.output !== previous.output) changes.push("output");
      if (current.model !== previous.model) changes.push("model");
      if (current.success !== previous.success) changes.push("success");
      if (current.latencyMs !== previous.latencyMs) changes.push("latency");

      if (changes.length) {
        lines.push(`${current.id}: changed ${changes.join(", ")}`);
      }
    }

    setDiffSummary(
      lines.length
        ? `Compared with ${previousRun.runId.slice(0, 8)}:\n${lines.join("\n")}`
        : `No step-level differences against ${previousRun.runId.slice(0, 8)}.`
    );
  };

  return (
    <section>
      <div className="topbar">
        <div>
          <h2 className="section-title">Trajectory viewer</h2>
          <p className="kicker">Reconstruct per-run step graphs, and inspect each step with one-click detail.</p>
        </div>
        <div className="toolbar">
          <select value={selectedRun} onChange={(e) => setSelectedRun(e.target.value)}>
            {runs.map((run) => (
              <option key={run.runId} value={run.runId}>
                {run.runId.slice(0, 8)} · {run.project}
              </option>
            ))}
          </select>
          <button className="btn" onClick={compareWithPreviousRun}>
            Diff with previous run
          </button>
          <button
            className="btn"
            onClick={async () => {
              if (!selectedRun) return;
              const artifact = await exportArtifact({ runIds: [selectedRun], format: "jsonl" });
              setMessage(`Trace snapshot exported to ${artifact.path}`);
            }}
          >
            Export trace snapshot
          </button>
        </div>
      </div>

      <div className="metrics">
        <div className="metric">
          <div className="metric-label">Nodes</div>
          <div className="metric-value">{metrics.toolCalls}</div>
        </div>
        <div className="metric">
          <div className="metric-label">Failed steps</div>
          <div className="metric-value">{metrics.failed}</div>
        </div>
        <div className="metric">
          <div className="metric-label">Avg latency</div>
          <div className="metric-value">{Math.round(metrics.averageLatency)} ms</div>
        </div>
        <div className="metric">
          <div className="metric-label">Token usage</div>
          <div className="metric-value">{metrics.tokens}</div>
        </div>
      </div>

      <div className="divider" />
      <div className="layout-two">
        <div className="chart-shell">
          <p className="muted-note" style={{ marginBottom: 8 }}>
            Step graph (React Flow)
          </p>
          <div className="flow-wrap">
            <ReactFlow nodes={nodes} edges={edges} zoomOnScroll fitView proOptions={{ hideAttribution: true }}>
              <Background />
              <Controls />
              <MiniMap />
            </ReactFlow>
          </div>
        </div>
        <div className="panel">
          <h3 className="panel-title">Step detail list</h3>
          <div className="step-list">
            {steps.map((step) => (
              <div key={step.id} className={`step-item ${expanded[step.id] ? "active" : ""}`}>
                <button
                  type="button"
                  onClick={() => toggleExpanded(step.id)}
                  className="btn"
                  style={{ marginBottom: 10, display: "inline-flex", alignItems: "center", gap: 6 }}
                >
                  {expanded[step.id] ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
                  {step.id} · {step.stepType.toUpperCase()}
                </button>
                {expanded[step.id] && (
                  <div>
                    <p className="muted-note">{step.prompt}</p>
                    <p>
                      <span className="status-pill success">{step.success ? "success" : "error"}</span>
                    </p>
                    <p className="muted-note">
                      model: {step.model} · temp: {step.temperature} · latency: {step.latencyMs}ms
                    </p>
                    {step.toolName && <p className="muted-note">tool: {step.toolName}</p>}
                    <div className="output-log mono">{step.output}</div>
                    <button className="btn" style={{ marginTop: 10 }} onClick={() => navigator.clipboard?.writeText(step.id)}>
                      <Copy size={14} /> Copy step id
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
          {diffSummary ? <pre className="output-log mono" style={{ marginTop: 10 }}>{diffSummary}</pre> : null}
          <p className="muted-note">{anyExpanded ? message : message || "Expand a step to inspect details."}</p>
        </div>
      </div>
    </section>
  );
}
