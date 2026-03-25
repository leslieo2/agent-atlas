import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import * as runApi from "@/src/entities/run/api";
import * as trajectoryApi from "@/src/entities/trajectory/api";
import { renderWithQueryClient } from "@/test/setup";
import PlaygroundWorkspace from "@/src/widgets/playground-workspace/PlaygroundWorkspace";

vi.mock("@/src/entities/run/api", () => ({
  listRuns: vi.fn(),
  createRun: vi.fn(),
  getRun: vi.fn()
}));

vi.mock("@/src/entities/trajectory/api", () => ({
  getTrajectory: vi.fn()
}));

type MockedApiFn = ReturnType<typeof vi.fn>;

const runs = [
  {
    runId: "run-play",
    inputSummary: "play",
    status: "succeeded" as const,
    latencyMs: 2,
    tokenCost: 1,
    toolCalls: 0,
    project: "playground",
    dataset: "crm-v2",
    model: "gpt-4.1-mini",
    agentType: "openai-agents-sdk",
    tags: [],
    createdAt: "2026-03-24T00:00:00Z"
  }
];

describe("Playground integration", () => {
  beforeEach(() => {
    (runApi.listRuns as unknown as MockedApiFn).mockReset();
    (runApi.createRun as unknown as MockedApiFn).mockReset();
    (runApi.getRun as unknown as MockedApiFn).mockReset();
    (trajectoryApi.getTrajectory as unknown as MockedApiFn).mockReset();
    (runApi.listRuns as unknown as MockedApiFn).mockResolvedValue(runs);
    (runApi.createRun as unknown as MockedApiFn).mockResolvedValue({
      ...runs[0],
      runId: "run-play-new",
      status: "queued"
    });
    (runApi.getRun as unknown as MockedApiFn)
      .mockResolvedValueOnce({
        ...runs[0],
        runId: "run-play-new",
        status: "running",
        latencyMs: 0,
        tokenCost: 0
      })
      .mockResolvedValueOnce({
        ...runs[0],
        runId: "run-play-new",
        status: "succeeded",
        latencyMs: 3412,
        tokenCost: 66
      })
      .mockResolvedValue({
        ...runs[0],
        runId: "run-play-new",
        status: "succeeded",
        latencyMs: 3412,
        tokenCost: 66
      });
    (trajectoryApi.getTrajectory as unknown as MockedApiFn).mockResolvedValue([
      {
        id: "s1",
        runId: "run-play-new",
        stepType: "planner",
        prompt: "prompt",
        output: "planner output",
        model: "planner-v1",
        temperature: 0,
        latencyMs: 12,
        tokenUsage: 0,
        success: true
      }
    ]);
  });

  it("creates a run and opens latest trace", async () => {
    renderWithQueryClient(<PlaygroundWorkspace />);
    await waitFor(() => expect(runApi.listRuns).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Run now" }));
    await waitFor(() => expect(runApi.createRun).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/run_id:\s*run-play-new/)).toBeInTheDocument();
    expect(await screen.findByText(/status:\s*succeeded/)).toBeInTheDocument();
    expect(await screen.findByText(/token_cost:\s*66/)).toBeInTheDocument();
    expect(await screen.findByText(/trace:/)).toBeInTheDocument();
    expect(await screen.findByText(/s1 \| planner \| planner output/)).toBeInTheDocument();
    await waitFor(() => expect(runApi.getRun).toHaveBeenCalledWith("run-play-new"));
    await waitFor(() => expect(trajectoryApi.getTrajectory).toHaveBeenCalledWith("run-play-new"));

    fireEvent.click(screen.getByRole("button", { name: "Open latest trace" }));
    expect(await screen.findByText(/s1 \| planner \| planner output/)).toBeInTheDocument();
  });

  it("loads sample prompt preset", async () => {
    renderWithQueryClient(<PlaygroundWorkspace />);
    await waitFor(() => expect(runApi.listRuns).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Attach dataset sample" }));
    expect(screen.getByDisplayValue("Can you create a shipping itinerary?")).toBeInTheDocument();
  });
});
