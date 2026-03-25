import type { Edge, Node } from "reactflow";
import { MarkerType } from "reactflow";
import type { RunRecord } from "@/src/entities/run/model";
import type { TrajectoryStep } from "@/src/entities/trajectory/model";

const ROOT_X = 120;
const ROOT_Y = 120;
const COLUMN_WIDTH = 240;
const ROW_HEIGHT = 160;

function buildParentMap(steps: TrajectoryStep[]) {
  const stepIds = new Set(steps.map((step) => step.id));

  return new Map(
    steps.flatMap((step) => {
      const parentStepId = step.parentStepId ?? null;
      if (!parentStepId || !stepIds.has(parentStepId)) {
        return [];
      }
      return [[step.id, parentStepId] as const];
    })
  );
}

function buildDepthMap(steps: TrajectoryStep[], parentById: Map<string, string>) {
  if (!steps.length) {
    return new Map<string, number>();
  }

  if (!parentById.size) {
    return new Map(steps.map((step, index) => [step.id, index]));
  }

  const childrenById = new Map<string, string[]>();
  for (const step of steps) {
    childrenById.set(step.id, []);
  }

  for (const [stepId, parentStepId] of parentById.entries()) {
    childrenById.get(parentStepId)?.push(stepId);
  }

  const depthById = new Map<string, number>();
  const queue = steps.filter((step) => !parentById.has(step.id)).map((step) => step.id);

  for (const rootId of queue) {
    depthById.set(rootId, 0);
  }

  while (queue.length) {
    const currentId = queue.shift();
    if (!currentId) continue;
    const currentDepth = depthById.get(currentId) ?? 0;

    for (const childId of childrenById.get(currentId) ?? []) {
      const nextDepth = currentDepth + 1;
      if ((depthById.get(childId) ?? -1) < nextDepth) {
        depthById.set(childId, nextDepth);
      }
      queue.push(childId);
    }
  }

  for (const step of steps) {
    if (!depthById.has(step.id)) {
      depthById.set(step.id, 0);
    }
  }

  return depthById;
}

export function buildTrajectoryNodes(steps: TrajectoryStep[], focusedStepId: string): Node[] {
  const parentById = buildParentMap(steps);
  const depthById = buildDepthMap(steps, parentById);
  const nextRowByDepth = new Map<number, number>();

  return steps.map((step) => {
    const depth = depthById.get(step.id) ?? 0;
    const rowIndex = nextRowByDepth.get(depth) ?? 0;
    nextRowByDepth.set(depth, rowIndex + 1);

    return {
      id: step.id,
      position: {
        x: ROOT_X + depth * COLUMN_WIDTH,
        y: ROOT_Y + rowIndex * ROW_HEIGHT
      },
      data: {
        label: `${step.stepType.toUpperCase()} · ${step.toolName || step.model} · ${step.success ? "OK" : "ERR"}`
      },
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
    };
  });
}

export function buildTrajectoryEdges(steps: TrajectoryStep[]): Edge[] {
  const parentById = buildParentMap(steps);

  if (!parentById.size) {
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

  return steps
    .filter((step) => parentById.has(step.id))
    .map((step) => {
      const parentStepId = parentById.get(step.id) as string;
      return {
        id: `e-${parentStepId}-${step.id}`,
        source: parentStepId,
        target: step.id,
        animated: true,
        style: { stroke: "#6bc7ff" },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: "#6bc7ff"
        }
      };
    });
}

export function getTrajectoryMetrics(steps: TrajectoryStep[]) {
  return {
    toolCalls: steps.length,
    failed: steps.filter((step) => !step.success).length,
    averageLatency: steps.reduce((acc, step) => acc + step.latencyMs, 0) / Math.max(steps.length, 1),
    tokens: steps.reduce((acc, step) => acc + step.tokenUsage, 0)
  };
}

function normalizeInputSummary(summary: string) {
  return summary.trim().replace(/\s+/g, " ").toLowerCase();
}

function getCreatedAtTimestamp(run: RunRecord) {
  const timestamp = Date.parse(run.createdAt);
  return Number.isNaN(timestamp) ? null : timestamp;
}

function isComparableRun(candidate: RunRecord, currentRun: RunRecord) {
  return (
    candidate.runId !== currentRun.runId &&
    candidate.project === currentRun.project &&
    candidate.dataset === currentRun.dataset &&
    candidate.agentType === currentRun.agentType &&
    normalizeInputSummary(candidate.inputSummary) === normalizeInputSummary(currentRun.inputSummary)
  );
}

export function findPreviousComparableRun(runs: RunRecord[], currentRun?: RunRecord) {
  if (!currentRun) {
    return undefined;
  }

  const currentTimestamp = getCreatedAtTimestamp(currentRun);
  const comparableRuns = runs
    .filter((candidate) => isComparableRun(candidate, currentRun))
    .filter((candidate) => {
      const candidateTimestamp = getCreatedAtTimestamp(candidate);

      if (currentTimestamp === null || candidateTimestamp === null) {
        return true;
      }

      return candidateTimestamp < currentTimestamp;
    })
    .sort((left, right) => {
      const leftTimestamp = getCreatedAtTimestamp(left);
      const rightTimestamp = getCreatedAtTimestamp(right);

      if (leftTimestamp === null || rightTimestamp === null) {
        return runs.findIndex((run) => run.runId === left.runId) - runs.findIndex((run) => run.runId === right.runId);
      }

      return rightTimestamp - leftTimestamp;
    });

  return comparableRuns[0];
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
