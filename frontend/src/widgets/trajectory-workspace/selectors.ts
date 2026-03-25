import type { Edge, Node } from "reactflow";
import { MarkerType } from "reactflow";
import type { TrajectoryStep } from "@/src/entities/trajectory/model";

export function buildTrajectoryNodes(steps: TrajectoryStep[], focusedStepId: string): Node[] {
  return steps.map((step, index) => ({
    id: step.id,
    position: { x: 120 + index * 240, y: 120 },
    data: { label: `${step.stepType.toUpperCase()} ${step.success ? "OK" : "ERR"}` },
    type: "default",
    style: {
      borderColor: focusedStepId === step.id ? "#5bc0ff" : step.success ? "#6ee7b7" : "#ff7a87",
      borderWidth: 2,
      borderRadius: 16,
      width: 156,
      background: "#0f162d",
      color: "#f2f6ff",
      textAlign: "center",
      boxShadow: focusedStepId === step.id ? "0 0 0 1px rgba(91,192,255,0.15)" : "none"
    }
  }));
}

export function buildTrajectoryEdges(steps: TrajectoryStep[]): Edge[] {
  return steps.slice(0, -1).map((step, index) => ({
    id: `e-${step.id}-${steps[index + 1].id}`,
    source: step.id,
    target: steps[index + 1].id,
    animated: true,
    style: { stroke: "#6bc7ff" },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: "#6bc7ff"
    }
  }));
}

export function getTrajectoryMetrics(steps: TrajectoryStep[]) {
  return {
    toolCalls: steps.length,
    failed: steps.filter((step) => !step.success).length,
    averageLatency: steps.reduce((acc, step) => acc + step.latencyMs, 0) / Math.max(steps.length, 1),
    tokens: steps.reduce((acc, step) => acc + step.tokenUsage, 0)
  };
}

export function compareTrajectories(currentSteps: TrajectoryStep[], previousSteps: TrajectoryStep[], previousRunId: string) {
  const maxLength = Math.max(currentSteps.length, previousSteps.length);
  const lines: string[] = [];

  for (let index = 0; index < maxLength; index += 1) {
    const current = currentSteps[index];
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

  return lines.length
    ? `Compared with ${previousRunId.slice(0, 8)}:\n${lines.join("\n")}`
    : `No step-level differences against ${previousRunId.slice(0, 8)}.`;
}

