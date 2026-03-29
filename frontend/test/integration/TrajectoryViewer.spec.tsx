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
  exportArtifact: vi.fn(),
  getArtifactDownloadUrl: vi.fn(() => "http://127.0.0.1:8000/api/v1/artifacts/artifact-001")
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
    agentId: "customer_service",
    model: "gpt-5.4-mini",
    agentType: "openai-agents-sdk",
    entrypoint: "app.agent_plugins.customer_service:build_agent",
    executionBackend: "docker",
    containerImage: "agent-atlas-backend:test",
    resolvedModel: "gpt-5.4-mini",
    errorCode: null,
    errorMessage: null,
    tags: ["retry", "support"],
    createdAt: "2026-03-24T01:00:00Z",
    projectMetadata: {
      prompt: "Retry the failed support run."
    },
    provenance: {
      artifactRef: "source://customer_service@fingerprint-current",
      imageRef: null,
      publishedAgentSnapshot: {
        runtime_artifact: {
          build_status: "ready",
          source_fingerprint: "fingerprint-current",
          artifact_ref: "source://customer_service@fingerprint-current",
          image_ref: null
        }
      }
    }
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
    agentId: "basic",
    model: "gpt-5.4-mini",
    agentType: "openai-agents-sdk",
    entrypoint: "app.agent_plugins.basic:build_agent",
    executionBackend: "local",
    containerImage: null,
    resolvedModel: "gpt-5.4-mini",
    errorCode: null,
    errorMessage: null,
    tags: [],
    createdAt: "2026-03-24T00:30:00Z"
  },
  {
    runId: "run-previous",
    inputSummary: "different prompt, still comparable",
    status: "failed" as const,
    latencyMs: 90,
    tokenCost: 10,
    toolCalls: 0,
    project: "project-a",
    dataset: "dataset-a",
    agentId: "customer_service",
    model: "gpt-5.4-mini",
    agentType: "openai-agents-sdk",
    entrypoint: "app.agent_plugins.customer_service:build_agent",
    executionBackend: "docker",
    containerImage: "agent-atlas-backend:test",
    resolvedModel: "gpt-5.4-mini",
    errorCode: "rate_limited",
    errorMessage: "provider rate limit exceeded",
    tags: [],
    createdAt: "2026-03-23T23:00:00Z",
    provenance: {
      artifactRef: "source://customer_service@fingerprint-previous",
      imageRef: null,
      publishedAgentSnapshot: {
        runtime_artifact: {
          build_status: "ready",
          source_fingerprint: "fingerprint-previous",
          artifact_ref: "source://customer_service@fingerprint-previous",
          image_ref: null
        }
      }
    }
  },
  {
    runId: "run-older",
    inputSummary: "older prompt",
    status: "succeeded" as const,
    latencyMs: 88,
    tokenCost: 12,
    toolCalls: 0,
    project: "project-a",
    dataset: "dataset-a",
    agentId: "customer_service",
    model: "gpt-5.4-mini",
    agentType: "openai-agents-sdk",
    entrypoint: "app.agent_plugins.customer_service:build_agent",
    executionBackend: "docker",
    containerImage: "agent-atlas-backend:test",
    resolvedModel: "gpt-5.4-mini",
    errorCode: null,
    errorMessage: null,
    tags: [],
    createdAt: "2026-03-23T22:00:00Z",
    provenance: {
      artifactRef: "source://customer_service@fingerprint-older",
      imageRef: null,
      publishedAgentSnapshot: {
        runtime_artifact: {
          build_status: "ready",
          source_fingerprint: "fingerprint-older",
          artifact_ref: "source://customer_service@fingerprint-older",
          image_ref: null
        }
      }
    }
  }
];

const currentSteps = [
  {
    id: "s1",
    runId: "run-current",
    stepType: "planner" as const,
    prompt: "plan",
    output: "current planner output",
    model: null,
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
    model: null,
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
    model: null,
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
    model: "gpt-5.4-mini",
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
    model: null,
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

  it("renders trajectory and compares against the selected run inside the same scope", async () => {
    renderWithQueryClient(<TrajectoryWorkspace />);

    expect(await screen.findByText("Loaded 4 steps.")).toBeInTheDocument();
    expect(screen.getByText("current planner output")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /s1/i })).toBeInTheDocument();
    expect(screen.getByTestId("graph-node-ids")).toHaveTextContent("s1|s2|s3|s4");
    expect(screen.getByTestId("graph-edge-pairs")).toHaveTextContent("s1->s2|s1->s3|s2->s4");

    fireEvent.change(screen.getByLabelText("Compare run"), { target: { value: "run-older" } });
    fireEvent.click(screen.getByRole("button", { name: "Compare selected run" }));
    await waitFor(() => {
      expect(screen.getByText(/Compared with run-olde/)).toBeInTheDocument();
    });
  });

  it("limits compare options to runs in the same project dataset and agent scope", async () => {
    renderWithQueryClient(<TrajectoryWorkspace />);

    expect(await screen.findByText("Loaded 4 steps.")).toBeInTheDocument();
    const compareSelect = screen.getByLabelText("Compare run");

    expect(screen.getByRole("option", { name: /run-previ/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /run-older/i })).toBeInTheDocument();
    expect(compareSelect).not.toHaveTextContent("run-unrelated-seed");
  });

  it("shows a compare empty state when the selected run has no peers in scope", async () => {
    (runApi.listRuns as unknown as MockedApiFn).mockResolvedValue([mockedRuns[0], mockedRuns[1]]);

    renderWithQueryClient(<TrajectoryWorkspace />);

    expect(await screen.findByText("Loaded 4 steps.")).toBeInTheDocument();
    expect(screen.getByLabelText("Compare run")).toBeDisabled();
    expect(screen.getByText("No comparable runs found in this project / dataset / agent scope.")).toBeInTheDocument();
  });

  it("exports trace snapshot for selected run", async () => {
    renderWithQueryClient(<TrajectoryWorkspace />);
    expect(await screen.findByText("Loaded 4 steps.")).toBeInTheDocument();
    await screen.findByText("Export Run JSONL");
    fireEvent.click(screen.getByRole("button", { name: "Export Run JSONL" }));

    await waitFor(() => {
      expect(screen.getByText("Run exported as JSONL.")).toBeInTheDocument();
    });
    expect(screen.getByText("Run run-curr · 12 bytes")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download JSONL" })).toHaveAttribute(
      "href",
      "http://127.0.0.1:8000/api/v1/artifacts/artifact-001"
    );
  });

  it("links rerun in playground with the selected run context", async () => {
    renderWithQueryClient(<TrajectoryWorkspace />);

    expect(await screen.findByText("Loaded 4 steps.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Rerun in Playground" })).toHaveAttribute(
      "href",
      "/playground?agent=customer_service&dataset=dataset-a&prompt=Retry+the+failed+support+run.&tags=retry%2Csupport"
    );
  });

  it("shows artifact handoff summary from run provenance", async () => {
    renderWithQueryClient(<TrajectoryWorkspace />);

    expect(await screen.findByText("Loaded 4 steps.")).toBeInTheDocument();
    expect(screen.getByText("source://customer_service@fingerprint-current")).toBeInTheDocument();
    expect(screen.getByText(/source_fingerprint: fingerprint-current/)).toBeInTheDocument();
    expect(screen.getByText(/build_status: ready/)).toBeInTheDocument();
  });
});
