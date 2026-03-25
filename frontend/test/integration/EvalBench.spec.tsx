import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import * as artifactApi from "@/src/entities/artifact/api";
import * as datasetApi from "@/src/entities/dataset/api";
import * as evalApi from "@/src/entities/eval/api";
import * as runApi from "@/src/entities/run/api";
import * as trajectoryApi from "@/src/entities/trajectory/api";
import EvalWorkspace from "@/src/widgets/eval-workspace/EvalWorkspace";

vi.mock("@/src/entities/dataset/api", () => ({
  listDatasets: vi.fn(),
  createDataset: vi.fn()
}));

vi.mock("@/src/entities/run/api", () => ({
  listRuns: vi.fn()
}));

vi.mock("@/src/entities/eval/api", () => ({
  createEvalJob: vi.fn()
}));

vi.mock("@/src/entities/trajectory/api", () => ({
  getTrajectory: vi.fn()
}));

vi.mock("@/src/entities/artifact/api", () => ({
  exportArtifact: vi.fn()
}));

type MockedApiFn = ReturnType<typeof vi.fn>;

describe("EvalBench integration", () => {
  beforeEach(() => {
    (datasetApi.listDatasets as unknown as MockedApiFn).mockReset();
    (datasetApi.createDataset as unknown as MockedApiFn).mockReset();
    (runApi.listRuns as unknown as MockedApiFn).mockReset();
    (evalApi.createEvalJob as unknown as MockedApiFn).mockReset();
    (trajectoryApi.getTrajectory as unknown as MockedApiFn).mockReset();
    (artifactApi.exportArtifact as unknown as MockedApiFn).mockReset();

    (datasetApi.listDatasets as unknown as MockedApiFn).mockResolvedValue([{ name: "crm-v2", rows: [] }]);
    (datasetApi.createDataset as unknown as MockedApiFn).mockResolvedValue({ name: "crm-v2", rows: [] });
    (runApi.listRuns as unknown as MockedApiFn).mockResolvedValue([
      {
        runId: "run-eval",
        inputSummary: "eval base",
        status: "succeeded" as const,
        latencyMs: 4,
        tokenCost: 8,
        toolCalls: 2,
        project: "proj-a",
        dataset: "crm-v2",
        model: "gpt-4.1-mini",
        agentType: "openai-agents-sdk",
        tags: [],
        createdAt: "2026-03-24T00:00:00Z"
      }
    ]);
    (evalApi.createEvalJob as unknown as MockedApiFn).mockResolvedValue({
      jobId: "job-001",
      runIds: ["run-eval"],
      dataset: "crm-v2",
      status: "done",
      results: [
        {
          sampleId: "s-1",
          runId: "run-eval",
          input: "sample input",
          status: "pass",
          score: 0.91
        },
        {
          sampleId: "s-2",
          runId: "run-eval",
          input: "failing sample",
          status: "fail",
          score: 0.43,
          reason: "tool mismatch"
        }
      ],
      createdAt: "2026-03-24T00:00:00Z"
    });
    (artifactApi.exportArtifact as unknown as MockedApiFn).mockResolvedValue({
      artifactId: "artifact-001",
      path: "/tmp/eval-artifact.jsonl",
      sizeBytes: 42
    });
    (trajectoryApi.getTrajectory as unknown as MockedApiFn).mockResolvedValue([
      {
        id: "e1",
        runId: "run-eval",
        stepType: "planner",
        prompt: "eval prompt",
        output: "eval output",
        model: "planner-v1",
        temperature: 0,
        latencyMs: 12,
        tokenUsage: 0,
        success: true
      }
    ]);
  });

  it("runs eval job and exports the active run as jsonl artifacts", async () => {
    render(<EvalWorkspace />);
    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(runApi.listRuns).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Run batch eval" }));
    expect(await screen.findByText(/Eval job job-001 finished with status done/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Export JSONL" }));
    expect(artifactApi.exportArtifact).toHaveBeenCalledWith({
      runIds: ["run-eval"],
      format: "jsonl"
    });
    expect(await screen.findByText("Exported JSONL artifacts to /tmp/eval-artifact.jsonl")).toBeInTheDocument();
  });

  it("compares eval rows and drills into a filtered failure sample", async () => {
    render(<EvalWorkspace />);
    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(runApi.listRuns).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Run batch eval" }));
    expect(await screen.findByText(/Eval job job-001 finished with status done/)).toBeInTheDocument();
    expect(screen.getByText("Failing samples (1)")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("sample id / run id"), {
      target: { value: "s-2" }
    });
    expect(screen.getByRole("row", { name: /s-2/ })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("row", { name: /s-2/ }));
    expect(await screen.findByText("Trajectory drill-down · sample s-2")).toBeInTheDocument();
    expect(screen.getByText("e1 · PLANNER · success")).toBeInTheDocument();
  });
});
