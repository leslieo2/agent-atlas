import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import StepReplayPanel from "@/components/StepReplayPanel";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  listRuns: vi.fn(),
  getTrajectory: vi.fn(),
  createReplay: vi.fn(),
  createRun: vi.fn()
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
    (api.listRuns as unknown as MockedApiFn).mockReset();
    (api.getTrajectory as unknown as MockedApiFn).mockReset();
    (api.createReplay as unknown as MockedApiFn).mockReset();
    (api.createRun as unknown as MockedApiFn).mockReset();
    (api.listRuns as unknown as MockedApiFn).mockResolvedValue(mockedRuns);
    (api.getTrajectory as unknown as MockedApiFn).mockResolvedValue(steps);
    (api.createReplay as unknown as MockedApiFn).mockResolvedValue({
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
    (api.createRun as unknown as MockedApiFn).mockResolvedValue({
      ...mockedRuns[0],
      runId: "run-replay-candidate"
    });
  });

  it("replays a step and writes diff", async () => {
    render(<StepReplayPanel />);

    expect(await screen.findByText(/Step replay/)).toBeInTheDocument();
    expect(screen.getByText("run-step · project-a")).toBeInTheDocument();

    const editedPrompt = screen.getByLabelText("Editable prompt");
    fireEvent.change(editedPrompt, { target: { value: "patched prompt" } });

    fireEvent.click(screen.getByRole("button", { name: "Replay step" }));
    const diffLine = await screen.findByText((content) => {
      const normalized = content.replace(/\s+/g, " ").trim();
      return normalized.startsWith("Replay diff:");
    });
    expect(diffLine).toBeInTheDocument();
  });

  it("promotes replay result to new run", async () => {
    render(<StepReplayPanel />);
    expect(await screen.findByText(/Step replay/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Replay step" }));
    fireEvent.click(screen.getByRole("button", { name: "Promote to new run" }));
    expect(
      await screen.findByText(/Promoted replay to new run run-replay-candidate/)
    ).toBeInTheDocument();
  });
});
