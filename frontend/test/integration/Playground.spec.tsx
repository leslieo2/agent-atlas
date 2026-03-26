import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import * as agentApi from "@/src/entities/agent/api";
import * as datasetApi from "@/src/entities/dataset/api";
import * as runApi from "@/src/entities/run/api";
import * as traceApi from "@/src/entities/trace/api";
import * as trajectoryApi from "@/src/entities/trajectory/api";
import { renderWithQueryClient } from "@/test/setup";
import PlaygroundWorkspace from "@/src/widgets/playground-workspace/PlaygroundWorkspace";

vi.mock("@/src/entities/agent/api", () => ({
  listAgents: vi.fn()
}));

vi.mock("@/src/entities/dataset/api", () => ({
  listDatasets: vi.fn()
}));

vi.mock("@/src/entities/run/api", () => ({
  listRuns: vi.fn(),
  createRun: vi.fn(),
  getRun: vi.fn(),
  terminateRun: vi.fn()
}));

vi.mock("@/src/entities/trajectory/api", () => ({
  getTrajectory: vi.fn()
}));

vi.mock("@/src/entities/trace/api", () => ({
  listRunTraces: vi.fn()
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
    agentId: "customer_service",
    model: "gpt-4.1-mini",
    agentType: "openai-agents-sdk",
    tags: [],
    createdAt: "2026-03-24T00:00:00Z"
  }
];

describe("Playground integration", () => {
  beforeEach(() => {
    (agentApi.listAgents as unknown as MockedApiFn).mockReset();
    (datasetApi.listDatasets as unknown as MockedApiFn).mockReset();
    (runApi.listRuns as unknown as MockedApiFn).mockReset();
    (runApi.createRun as unknown as MockedApiFn).mockReset();
    (runApi.getRun as unknown as MockedApiFn).mockReset();
    (runApi.terminateRun as unknown as MockedApiFn).mockReset();
    (traceApi.listRunTraces as unknown as MockedApiFn).mockReset();
    (trajectoryApi.getTrajectory as unknown as MockedApiFn).mockReset();
    (agentApi.listAgents as unknown as MockedApiFn).mockResolvedValue([
      {
        agentId: "basic",
        name: "Basic",
        description: "Minimal smoke agent.",
        framework: "openai-agents-sdk",
        entrypoint: "app.registered_agents.basic:build_agent",
        defaultModel: "gpt-4.1-mini",
        tags: ["example", "smoke"]
      },
      {
        agentId: "customer_service",
        name: "Customer Service",
        description: "Support agent.",
        framework: "openai-agents-sdk",
        entrypoint: "app.registered_agents.customer_service:build_agent",
        defaultModel: "gpt-4.1-mini",
        tags: ["example", "support"]
      }
    ]);
    (datasetApi.listDatasets as unknown as MockedApiFn).mockResolvedValue([{ name: "customer-live", rows: [] }]);
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
    (runApi.terminateRun as unknown as MockedApiFn).mockResolvedValue({
      runId: "run-play",
      terminated: true,
      status: "terminated",
      terminationReason: "terminated by user"
    });
    (traceApi.listRunTraces as unknown as MockedApiFn).mockResolvedValue([
      {
        runId: "run-play-new",
        spanId: "trace-1",
        parentSpanId: null,
        stepType: "planner",
        input: {},
        output: { output: "planner trace output" },
        latencyMs: 12,
        tokenUsage: 0,
        receivedAt: "2026-03-24T00:00:00Z"
      }
    ]);
    (trajectoryApi.getTrajectory as unknown as MockedApiFn).mockResolvedValue([
      {
        id: "s1",
        runId: "run-play-new",
        stepType: "planner",
        prompt: "prompt",
        output: "planner output",
        model: null,
        temperature: 0,
        latencyMs: 12,
        tokenUsage: 0,
        success: true
      }
    ]);
  });

  it("creates a run and opens latest trace", async () => {
    renderWithQueryClient(<PlaygroundWorkspace />);
    await waitFor(() => expect(agentApi.listAgents).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(runApi.listRuns).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Run now" }));
    await waitFor(() => expect(runApi.createRun).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/run_id:\s*run-play-new/)).toBeInTheDocument();
    expect(await screen.findByText(/status:\s*succeeded/)).toBeInTheDocument();
    expect(await screen.findByText(/token_cost:\s*66/)).toBeInTheDocument();
    expect(await screen.findByText(/trace:/)).toBeInTheDocument();
    expect(await screen.findByText(/trace-1 \| planner \| planner trace output/)).toBeInTheDocument();
    await waitFor(() => expect(runApi.getRun).toHaveBeenCalledWith("run-play-new"));
    await waitFor(() => expect(traceApi.listRunTraces).toHaveBeenCalledWith("run-play-new"));

    fireEvent.click(screen.getByRole("button", { name: "Refresh live trace" }));
    expect(await screen.findByText(/trace-1 \| planner \| planner trace output/)).toBeInTheDocument();
  });

  it("loads sample prompt preset", async () => {
    renderWithQueryClient(<PlaygroundWorkspace />);
    await waitFor(() => expect(agentApi.listAgents).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(runApi.listRuns).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getAllByRole("combobox")[1], { target: { value: "customer-live" } });
    fireEvent.click(screen.getByRole("button", { name: "Attach dataset sample" }));
    expect(screen.getByDisplayValue("Can you create a shipping itinerary?")).toBeInTheDocument();
  });

  it("terminates the latest run", async () => {
    renderWithQueryClient(<PlaygroundWorkspace />);
    await waitFor(() => expect(agentApi.listAgents).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(runApi.listRuns).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("run-play")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Terminate run" }));
    await waitFor(() => expect(runApi.terminateRun).toHaveBeenCalledWith("run-play"));
    expect(await screen.findByText(/termination_reason:\s*terminated by user/)).toBeInTheDocument();
  });

  it("allows prompt-only execution when no dataset exists", async () => {
    (datasetApi.listDatasets as unknown as MockedApiFn).mockResolvedValue([]);

    renderWithQueryClient(<PlaygroundWorkspace />);

    await waitFor(() => expect(agentApi.listAgents).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/No dataset attached. Playground will run prompt-only until you select one./)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Run now" }));

    await waitFor(() =>
      expect(runApi.createRun).toHaveBeenCalledWith(
        expect.objectContaining({
          dataset: null,
          agentId: "basic"
        })
      )
    );
  });
});
