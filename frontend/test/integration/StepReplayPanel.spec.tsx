import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import * as replayApi from "@/src/entities/replay/api";
import * as runApi from "@/src/entities/run/api";
import * as trajectoryApi from "@/src/entities/trajectory/api";
import { renderWithQueryClient } from "@/test/setup";
import ReplayWorkspace from "@/src/widgets/replay-workspace/ReplayWorkspace";

vi.mock("@/src/entities/run/api", () => ({
  listRuns: vi.fn(),
  createRun: vi.fn()
}));

vi.mock("@/src/entities/trajectory/api", () => ({
  getTrajectory: vi.fn()
}));

vi.mock("@/src/entities/replay/api", () => ({
  createReplay: vi.fn()
}));

type MockedApiFn = ReturnType<typeof vi.fn>;

const mockedRuns = [
  {
    runId: "run-step",
    inputSummary: "replay seed",
    status: "succeeded" as const,
    latencyMs: 10,
    tokenCost: 20,
    toolCalls: 2,
    project: "project-a",
    dataset: "dataset-a",
    model: "gpt-4.1-mini",
    agentType: "openai-agents-sdk",
    tags: [],
    createdAt: "2026-03-24T00:00:00Z"
  }
];

const steps = [
  {
    id: "step-replay",
    runId: "run-step",
    stepType: "llm" as const,
    prompt: "base prompt",
    output: "base output",
    model: "gpt-4.1-mini",
    temperature: 0,
    latencyMs: 100,
    tokenUsage: 40,
    success: true
  }
];

describe("StepReplayPanel integration", () => {
  beforeEach(() => {
    (runApi.listRuns as unknown as MockedApiFn).mockReset();
    (trajectoryApi.getTrajectory as unknown as MockedApiFn).mockReset();
    (replayApi.createReplay as unknown as MockedApiFn).mockReset();
    (runApi.createRun as unknown as MockedApiFn).mockReset();
    (runApi.listRuns as unknown as MockedApiFn).mockResolvedValue(mockedRuns);
    (trajectoryApi.getTrajectory as unknown as MockedApiFn).mockResolvedValue(steps);
    (replayApi.createReplay as unknown as MockedApiFn).mockResolvedValue({
      replayId: "replay-001",
      runId: "run-step",
      stepId: "step-replay",
      baselineOutput: "base output",
      replayOutput: "new output",
      diff: "patched",
      model: "gpt-4.1-mini",
      temperature: 0,
      startedAt: "2026-03-24T00:00:00Z",
      updatedPrompt: "patched prompt"
    });
    (runApi.createRun as unknown as MockedApiFn).mockResolvedValue({
      ...mockedRuns[0],
      runId: "run-replay-candidate"
    });
  });

  it("replays a step and writes diff", async () => {
    renderWithQueryClient(<ReplayWorkspace />);

    expect(await screen.findByText(/Step replay/)).toBeInTheDocument();
    expect(await screen.findByText("base output")).toBeInTheDocument();

    const editedPrompt = screen.getByLabelText("Editable prompt");
    fireEvent.change(editedPrompt, { target: { value: "patched prompt" } });

    fireEvent.click(screen.getByRole("button", { name: "Replay step" }));
    await waitFor(() => expect(replayApi.createReplay).toHaveBeenCalledTimes(1));
    const diffLine = await screen.findByText((content) => {
      const normalized = content.replace(/\s+/g, " ").trim();
      return normalized.startsWith("Replay diff:");
    });
    expect(diffLine).toBeInTheDocument();
    expect(await screen.findByText("new output")).toBeInTheDocument();
  });

  it("promotes replay result to new run", async () => {
    renderWithQueryClient(<ReplayWorkspace />);
    expect(await screen.findByText("base output")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Replay step" }));
    await waitFor(() => expect(replayApi.createReplay).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByRole("button", { name: "Promote to new run" }));
    await waitFor(() => expect(runApi.createRun).toHaveBeenCalledTimes(1));
    expect(
      await screen.findByText(/Promoted replay to new run run-replay-candidate/)
    ).toBeInTheDocument();
  });
});
