import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import * as artifactApi from "@/src/entities/artifact/api";
import * as datasetApi from "@/src/entities/dataset/api";
import * as evalApi from "@/src/entities/eval/api";
import * as runApi from "@/src/entities/run/api";
import * as trajectoryApi from "@/src/entities/trajectory/api";
import { renderWithQueryClient } from "@/test/setup";
import EvalWorkspace from "@/src/widgets/eval-workspace/EvalWorkspace";

vi.mock("@/src/entities/dataset/api", () => ({
  listDatasets: vi.fn(),
  createDataset: vi.fn()
}));

vi.mock("@/src/entities/run/api", () => ({
  listRuns: vi.fn()
}));

vi.mock("@/src/entities/eval/api", () => ({
  createEvalJob: vi.fn(),
  getEvalJob: vi.fn()
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
    (evalApi.getEvalJob as unknown as MockedApiFn).mockReset();
    (trajectoryApi.getTrajectory as unknown as MockedApiFn).mockReset();
    (artifactApi.exportArtifact as unknown as MockedApiFn).mockReset();

    (datasetApi.listDatasets as unknown as MockedApiFn).mockResolvedValue([
      {
        name: "crm-v2",
        rows: [
          {
            sampleId: "sample-1",
            input: "sample input",
            expected: "expected answer",
            tags: ["priority"]
          }
        ]
      }
    ]);
    (datasetApi.createDataset as unknown as MockedApiFn).mockResolvedValue({
      name: "crm-v2",
      rows: [
        {
          sampleId: "sample-1",
          input: "sample input",
          expected: "expected answer",
          tags: ["priority"]
        }
      ]
    });
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
      },
      {
        runId: "run-candidate",
        inputSummary: "eval candidate",
        status: "succeeded" as const,
        latencyMs: 5,
        tokenCost: 9,
        toolCalls: 2,
        project: "proj-a",
        dataset: "crm-v2",
        model: "gpt-4.1",
        agentType: "openai-agents-sdk",
        tags: ["candidate"],
        createdAt: "2026-03-24T00:05:00Z",
        projectMetadata: {
          candidate: {
            kind: "replay"
          }
        }
      }
    ]);
    (evalApi.createEvalJob as unknown as MockedApiFn).mockResolvedValue({
      jobId: "job-001",
      runIds: ["run-eval", "run-candidate"],
      dataset: "crm-v2",
      status: "queued",
      results: [],
      createdAt: "2026-03-24T00:00:00Z"
    });
    (evalApi.getEvalJob as unknown as MockedApiFn)
      .mockResolvedValueOnce({
        jobId: "job-001",
        runIds: ["run-eval", "run-candidate"],
        dataset: "crm-v2",
        status: "running",
        results: [],
        createdAt: "2026-03-24T00:00:00Z"
      })
      .mockResolvedValueOnce({
        jobId: "job-001",
        runIds: ["run-eval", "run-candidate"],
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
            sampleId: "s-1",
            runId: "run-candidate",
            input: "sample input",
            status: "pass",
            score: 0.97
          },
          {
            sampleId: "s-2",
            runId: "run-eval",
            input: "failing sample",
            status: "fail",
            score: 0.43,
            reason: "tool mismatch"
          },
          {
            sampleId: "s-2",
            runId: "run-candidate",
            input: "failing sample",
            status: "pass",
            score: 0.82
          }
        ],
        createdAt: "2026-03-24T00:00:00Z"
      });
    (artifactApi.exportArtifact as unknown as MockedApiFn).mockResolvedValue({
      artifactId: "artifact-001",
      format: "jsonl",
      runIds: ["run-eval", "run-candidate"],
      createdAt: "2026-03-24T00:00:00Z",
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
        model: null,
        temperature: 0,
        latencyMs: 12,
        tokenUsage: 0,
        success: true
      }
    ]);
  });

  it("runs eval job and exports the selected runs as jsonl artifacts", async () => {
    renderWithQueryClient(<EvalWorkspace initialRunIds={["run-eval", "run-candidate"]} />);
    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(runApi.listRuns).toHaveBeenCalledTimes(1));
    await screen.findByText(/run-cand.*candidate/i);
    await waitFor(() => expect(screen.getByRole("button", { name: "Run batch eval" })).toBeEnabled());

    fireEvent.click(screen.getByRole("button", { name: "Run batch eval" }));
    await waitFor(() => expect(evalApi.createEvalJob).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/Eval job job-001 finished with status done/)).toBeInTheDocument();
    await waitFor(() => expect(evalApi.getEvalJob).toHaveBeenCalledWith("job-001"));
    expect(evalApi.createEvalJob).toHaveBeenCalledWith({
      runIds: ["run-eval", "run-candidate"],
      dataset: "crm-v2",
      evaluators: ["rule", "judge", "tool-correctness"]
    });
    expect(screen.getByText(/run-cand .* success 100% .* avg score 0.9/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Export JSONL" }));
    await waitFor(() => {
      expect(artifactApi.exportArtifact).toHaveBeenCalledWith({
        runIds: ["run-eval", "run-candidate"],
        format: "jsonl"
      });
    });
    expect(await screen.findByText("Exported JSONL artifacts to /tmp/eval-artifact.jsonl")).toBeInTheDocument();
  });

  it("compares eval rows and drills into a filtered failure sample", async () => {
    renderWithQueryClient(<EvalWorkspace initialRunIds={["run-eval", "run-candidate"]} />);
    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(runApi.listRuns).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Run batch eval" }));
    expect(await screen.findByText(/Eval job job-001 finished with status done/)).toBeInTheDocument();
    await waitFor(() => expect(evalApi.getEvalJob).toHaveBeenCalledWith("job-001"));
    expect(screen.getByText("Failing samples (1)")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("sample id / run id"), {
      target: { value: "s-2" }
    });
    expect(screen.getByRole("row", { name: /run-eval.*s-2/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("row", { name: /run-eval.*s-2/i }));
    expect(await screen.findByText("Trajectory drill-down · sample s-2")).toBeInTheDocument();
    expect(screen.getByText("e1 · PLANNER · success")).toBeInTheDocument();
  });

  it("shows dataset preview details for the active dataset", async () => {
    renderWithQueryClient(<EvalWorkspace initialRunIds={["run-eval"]} />);

    expect(await screen.findByText("Inspect the active dataset before running eval")).toBeInTheDocument();
    expect(await screen.findByText("sample-1")).toBeInTheDocument();
    expect(screen.getByText("expected answer")).toBeInTheDocument();
    expect(screen.getByText("priority")).toBeInTheDocument();
  });

  it("disables eval actions when no dataset exists", async () => {
    (datasetApi.listDatasets as unknown as MockedApiFn).mockResolvedValue([]);

    renderWithQueryClient(<EvalWorkspace initialRunIds={["run-eval"]} />);

    expect(await screen.findByText("No dataset available. Upload a JSONL dataset before running eval.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run batch eval" })).toBeDisabled();
  });
});
