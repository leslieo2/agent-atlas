import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import Playground from "@/components/Playground";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  listRuns: vi.fn(),
  createRun: vi.fn(),
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
    (api.listRuns as unknown as MockedApiFn).mockReset();
    (api.createRun as unknown as MockedApiFn).mockReset();
    (api.getTrajectory as unknown as MockedApiFn).mockReset();
    (api.listRuns as unknown as MockedApiFn).mockResolvedValue(runs);
    (api.createRun as unknown as MockedApiFn).mockResolvedValue({
      ...runs[0],
      runId: "run-play-new"
    });
    (api.getTrajectory as unknown as MockedApiFn).mockResolvedValue([
      {
        id: "s1",
        runId: "run-play",
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
    render(<Playground />);
    await waitFor(() => expect(api.listRuns).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Run now" }));
    expect(api.createRun).toHaveBeenCalledTimes(1);
    expect(await screen.findByText(/run_id:\s*run-play-new/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Open latest trace" }));
    expect(await screen.findByText(/s1 \| planner \| planner output/)).toBeInTheDocument();
  });

  it("loads sample prompt preset", async () => {
    render(<Playground />);
    await waitFor(() => expect(api.listRuns).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Attach dataset sample" }));
    expect(screen.getByDisplayValue("Can you create a shipping itinerary?")).toBeInTheDocument();
  });
});
