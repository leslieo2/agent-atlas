import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import * as artifactApi from "@/src/entities/artifact/api";
import * as runApi from "@/src/entities/run/api";
import * as trajectoryApi from "@/src/entities/trajectory/api";
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
    runId: "run-previous",
    inputSummary: "previous run",
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
    success: true
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
    toolName: "search"
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
      runId === "run-current" ? currentSteps : previousSteps
    );
    (artifactApi.exportArtifact as unknown as MockedApiFn).mockResolvedValue({
      artifactId: "artifact-001",
      path: "/tmp/trajectory.jsonl",
      sizeBytes: 12
    });
  });

  it("renders trajectory and shows diffs against previous run", async () => {
    render(<TrajectoryWorkspace />);

    expect(await screen.findByText("Loaded 2 steps.")).toBeInTheDocument();
    expect(screen.getByText("current planner output")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /s1/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Diff with previous run" }));
    await waitFor(() => {
      expect(screen.getByText(/Compared with run-pre/)).toBeInTheDocument();
    });
  });

  it("exports trace snapshot for selected run", async () => {
    render(<TrajectoryWorkspace />);
    expect(await screen.findByText("Loaded 2 steps.")).toBeInTheDocument();
    await screen.findByText("Export trace snapshot");
    fireEvent.click(screen.getByRole("button", { name: "Export trace snapshot" }));

    await waitFor(() => {
      expect(screen.getByText(/Trace snapshot exported to/)).toBeInTheDocument();
    });
  });
});
