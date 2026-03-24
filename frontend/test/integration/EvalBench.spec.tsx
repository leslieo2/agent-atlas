import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import EvalBench from "@/components/EvalBench";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  listDatasets: vi.fn(),
  listRuns: vi.fn(),
  createEvalJob: vi.fn(),
  getTrajectory: vi.fn()
}));

type MockedApiFn = ReturnType<typeof vi.fn>;

describe("EvalBench integration", () => {
  beforeEach(() => {
    (api.listDatasets as unknown as MockedApiFn).mockReset();
    (api.listRuns as unknown as MockedApiFn).mockReset();
    (api.createEvalJob as unknown as MockedApiFn).mockReset();
    (api.getTrajectory as unknown as MockedApiFn).mockReset();

    (api.listDatasets as unknown as MockedApiFn).mockResolvedValue([{ name: "crm-v2", rows: [] }]);
    (api.listRuns as unknown as MockedApiFn).mockResolvedValue([
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
    (api.createEvalJob as unknown as MockedApiFn).mockResolvedValue({
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
        }
      ],
      createdAt: "2026-03-24T00:00:00Z"
    });
    (api.getTrajectory as unknown as MockedApiFn).mockResolvedValue([
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

  it("runs eval job and displays summary", async () => {
    render(<EvalBench />);

    expect(await screen.findByText("Load datasets and run an eval.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Run batch eval" }));
    expect(await screen.findByText(/Eval job job-001 finished with status done/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "View trajectory" }));
    expect(await screen.findByText("Trajectory drill-down · sample s-1")).toBeInTheDocument();
    expect(screen.getByText("e1 · PLANNER · success")).toBeInTheDocument();
  });
});
