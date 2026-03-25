import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import * as artifactApi from "@/src/entities/artifact/api";
import * as runApi from "@/src/entities/run/api";
import * as trajectoryApi from "@/src/entities/trajectory/api";
import { renderWithQueryClient } from "@/test/setup";
import TrajectoryWorkspace from "@/src/widgets/trajectory-workspace/TrajectoryWorkspace";

vi.mock("reactflow", () => {
  return {
    __esModule: true,
    default: () => <div>reactflow-mock</div>,
    Node: [],
    Edge: [],
    MarkerType: {
      ArrowClosed: "arrow-closed"
    },
    Background: () => <div />,
    Controls: () => <div />,
    MiniMap: () => <div />
  };
});

vi.mock("@/src/features/trajectory-graph/TrajectoryGraph", () => ({
  TrajectoryGraph: ({ nodes, edges }: { nodes: Array<{ id: string }>; edges: Array<{ source: string; target: string }> }) => (
    <div>
      <div>trajectory-graph-mock</div>
      <div data-testid="graph-node-ids">{nodes.map((node) => node.id).join("|")}</div>
      <div data-testid="graph-edge-pairs">{edges.map((edge) => `${edge.source}->${edge.target}`).join("|")}</div>
    </div>
  )
}));

vi.mock("@/src/entities/run/api", () => ({
  listRuns: vi.fn(),
}));

vi.mock("@/src/entities/trajectory/api", () => ({
  getTrajectory: vi.fn()
}));

vi.mock("@/src/entities/artifact/api", () => ({
  exportArtifact: vi.fn()
}));

const mockedRuns = [
  {
    runId: "run-current",
    inputSummary: "current run",
    status: "succeeded" as const,
    latencyMs: 100,
    tokenCost: 20,
    toolCalls: 0,
    project: "project-a",
    dataset: "dataset-a",
    model: "gpt-4.1-mini",
    agentType: "openai-agents-sdk",
    tags: [],
    createdAt: "2026-03-24T01:00:00Z"
  },
  {
    runId: "run-unrelated-seed",
    inputSummary: "seed run",
    status: "succeeded" as const,
    latencyMs: 80,
    tokenCost: 9,
    toolCalls: 0,
    project: "project-seed",
    dataset: "dataset-seed",
    model: "gpt-4.1-mini",
    agentType: "openai-agents-sdk",
    tags: [],
    createdAt: "2026-03-24T00:30:00Z"
  },
  {
    runId: "run-previous",
    inputSummary: "current run",
    status: "failed" as const,
    latencyMs: 90,
    tokenCost: 10,
    toolCalls: 0,
    project: "project-a",
    dataset: "dataset-a",
    model: "gpt-4.1-mini",
    agentType: "openai-agents-sdk",
    tags: [],
    createdAt: "2026-03-23T23:00:00Z"
  }
];

const currentSteps = [
  {
    id: "s1",
    runId: "run-current",
    stepType: "planner" as const,
    prompt: "plan",
    output: "current planner output",
    model: "planner-v1",
    temperature: 0,
    latencyMs: 10,
    tokenUsage: 0,
    success: true,
    parentStepId: null
  },
  {
    id: "s2",
    runId: "run-current",
    stepType: "tool" as const,
    prompt: "tool in",
    output: "current tool output",
    model: "planner-v1",
    temperature: 0,
    latencyMs: 8,
    tokenUsage: 0,
    success: false,
    toolName: "search",
    parentStepId: "s1"
  },
  {
    id: "s3",
    runId: "run-current",
    stepType: "tool" as const,
    prompt: "tool input b",
    output: "branch tool output",
    model: "planner-v1",
    temperature: 0,
    latencyMs: 6,
    tokenUsage: 0,
    success: true,
    toolName: "crm_lookup",
    parentStepId: "s1"
  },
  {
    id: "s4",
    runId: "run-current",
    stepType: "llm" as const,
    prompt: "summarize",
    output: "llm output",
    model: "gpt-4.1-mini",
    temperature: 0,
    latencyMs: 12,
    tokenUsage: 14,
    success: true,
    parentStepId: "s2"
  }
];

const previousSteps = [
  {
    id: "p1",
    runId: "run-previous",
    stepType: "planner" as const,
    prompt: "plan",
    output: "previous planner output",
    model: "planner-v1",
    temperature: 0,
    latencyMs: 8,
    tokenUsage: 0,
    success: true
  }
];

type MockedApiFn = ReturnType<typeof vi.fn>;

describe("TrajectoryViewer integration", () => {
  beforeEach(() => {
    (runApi.listRuns as unknown as MockedApiFn).mockReset();
    (trajectoryApi.getTrajectory as unknown as MockedApiFn).mockReset();
    (artifactApi.exportArtifact as unknown as MockedApiFn).mockReset();
    (runApi.listRuns as unknown as MockedApiFn).mockResolvedValue(mockedRuns);
    (trajectoryApi.getTrajectory as unknown as MockedApiFn).mockImplementation(async (runId: string) =>
      runId === "run-current" ? currentSteps : runId === "run-previous" ? previousSteps : []
    );
    (artifactApi.exportArtifact as unknown as MockedApiFn).mockResolvedValue({
      artifactId: "artifact-001",
      path: "/tmp/trajectory.jsonl",
      sizeBytes: 12
    });
  });

  it("renders trajectory and shows diffs against previous run", async () => {
    renderWithQueryClient(<TrajectoryWorkspace />);

    expect(await screen.findByText("Loaded 4 steps.")).toBeInTheDocument();
    expect(screen.getByText("current planner output")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /s1/i })).toBeInTheDocument();
    expect(screen.getByTestId("graph-node-ids")).toHaveTextContent("s1|s2|s3|s4");
    expect(screen.getByTestId("graph-edge-pairs")).toHaveTextContent("s1->s2|s1->s3|s2->s4");

    fireEvent.click(screen.getByRole("button", { name: "Diff with previous run" }));
    await waitFor(() => {
      expect(screen.getByText(/Compared with run-pre/)).toBeInTheDocument();
    });
  });

  it("does not compare against an unrelated earlier run", async () => {
    renderWithQueryClient(<TrajectoryWorkspace />);

    expect(await screen.findByText("Loaded 4 steps.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Diff with previous run" }));

    await waitFor(() => {
      expect(trajectoryApi.getTrajectory).toHaveBeenCalledWith("run-previous");
    });
    expect(trajectoryApi.getTrajectory).not.toHaveBeenCalledWith("run-unrelated-seed");
  });

  it("exports trace snapshot for selected run", async () => {
    renderWithQueryClient(<TrajectoryWorkspace />);
    expect(await screen.findByText("Loaded 4 steps.")).toBeInTheDocument();
    await screen.findByText("Export trace snapshot");
    fireEvent.click(screen.getByRole("button", { name: "Export trace snapshot" }));

    await waitFor(() => {
      expect(screen.getByText(/Trace snapshot exported to/)).toBeInTheDocument();
    });
  });
});
