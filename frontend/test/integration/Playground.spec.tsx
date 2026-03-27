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

const runningRun = {
  ...runs[0],
  status: "running" as const
};

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
        entrypoint: "app.agent_plugins.basic:build_agent",
        defaultModel: "gpt-4.1-mini",
        tags: ["example", "smoke"]
      },
      {
        agentId: "customer_service",
        name: "Customer Service",
        description: "Support agent.",
        framework: "openai-agents-sdk",
        entrypoint: "app.agent_plugins.customer_service:build_agent",
        defaultModel: "gpt-4.1-mini",
        tags: ["example", "support"]
      }
    ]);
    (datasetApi.listDatasets as unknown as MockedApiFn).mockResolvedValue([
      {
        name: "crm-v2",
        rows: [{ sampleId: "sample-001", input: "Can you create a shipping itinerary?" }]
      },
      {
        name: "support-incidents",
        rows: [{ sampleId: "sample-002", input: "Summarize the priority tickets from the incident queue." }]
      }
    ]);
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

    fireEvent.click(screen.getByRole("button", { name: "Load sample prompt" }));
    expect(screen.getByDisplayValue("Can you create a shipping itinerary?")).toBeInTheDocument();
  });

  it("attaches the selected dataset sample to the prompt", async () => {
    renderWithQueryClient(<PlaygroundWorkspace initialDataset="crm-v2" />);

    await waitFor(() => expect(agentApi.listAgents).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(runApi.listRuns).toHaveBeenCalledTimes(1));

    await waitFor(() => expect(screen.getByLabelText("Dataset")).toHaveValue("crm-v2"));
    fireEvent.click(screen.getByRole("button", { name: "Attach dataset sample" }));
    expect(screen.getByDisplayValue("Can you create a shipping itinerary?")).toBeInTheDocument();
  });

  it("submits the attached dataset when launched from new run context", async () => {
    renderWithQueryClient(<PlaygroundWorkspace initialDataset="crm-v2" />);

    await waitFor(() => expect(agentApi.listAgents).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(runApi.listRuns).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByLabelText("Dataset")).toHaveValue("crm-v2"));

    fireEvent.click(screen.getByRole("button", { name: "Run now" }));

    await waitFor(() =>
      expect(runApi.createRun).toHaveBeenCalledWith(
        expect.objectContaining({
          dataset: "crm-v2",
          agentId: "basic"
        })
      )
    );
  });

  it("terminates the latest run", async () => {
    (runApi.getRun as unknown as MockedApiFn).mockReset();
    (runApi.terminateRun as unknown as MockedApiFn).mockReset();
    (runApi.listRuns as unknown as MockedApiFn).mockResolvedValue([runningRun]);
    (runApi.getRun as unknown as MockedApiFn).mockResolvedValue(runningRun);
    (runApi.terminateRun as unknown as MockedApiFn).mockResolvedValue({
      runId: "run-play",
      terminated: true,
      status: "terminated",
      terminationReason: "terminated by user"
    });

    renderWithQueryClient(<PlaygroundWorkspace />);
    await waitFor(() => expect(agentApi.listAgents).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(runApi.listRuns).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("run-play")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Terminate run" }));
    await waitFor(() => expect(runApi.terminateRun).toHaveBeenCalledWith("run-play"));
    expect(await screen.findByText(/termination_reason:\s*terminated by user/)).toBeInTheDocument();
  });

  it("does not terminate a completed latest run", async () => {
    (runApi.getRun as unknown as MockedApiFn).mockReset();
    (runApi.getRun as unknown as MockedApiFn).mockResolvedValue(runs[0]);

    renderWithQueryClient(<PlaygroundWorkspace />);
    await waitFor(() => expect(agentApi.listAgents).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(runApi.listRuns).toHaveBeenCalledTimes(1));

    const terminateButton = screen.getByRole("button", { name: "Terminate run" });
    expect(terminateButton).toBeDisabled();

    fireEvent.click(terminateButton);
    expect(runApi.terminateRun).not.toHaveBeenCalled();
  });

  it("does not call terminate when the latest run finishes before the click resolves", async () => {
    (runApi.getRun as unknown as MockedApiFn).mockReset();
    (runApi.terminateRun as unknown as MockedApiFn).mockReset();
    (runApi.listRuns as unknown as MockedApiFn).mockResolvedValue([runningRun]);
    (runApi.getRun as unknown as MockedApiFn).mockResolvedValue(runs[0]);

    renderWithQueryClient(<PlaygroundWorkspace />);
    await waitFor(() => expect(agentApi.listAgents).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(runApi.listRuns).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Terminate run" }));

    await waitFor(() => expect(runApi.getRun).toHaveBeenCalledWith("run-play"));
    expect(runApi.terminateRun).not.toHaveBeenCalled();
    expect(await screen.findByText(/Run run-play is already succeeded and can no longer be terminated./)).toBeInTheDocument();
  });

  it("shows the API error when terminate fails", async () => {
    (runApi.getRun as unknown as MockedApiFn).mockReset();
    (runApi.terminateRun as unknown as MockedApiFn).mockReset();
    (runApi.listRuns as unknown as MockedApiFn).mockResolvedValue([runningRun]);
    (runApi.getRun as unknown as MockedApiFn).mockResolvedValue(runningRun);
    (runApi.terminateRun as unknown as MockedApiFn).mockRejectedValue(new Error("run not running or not found"));

    renderWithQueryClient(<PlaygroundWorkspace />);
    await waitFor(() => expect(agentApi.listAgents).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(runApi.listRuns).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Terminate run" }));

    await waitFor(() => expect(runApi.terminateRun).toHaveBeenCalledWith("run-play"));
    expect(await screen.findByText("run not running or not found")).toBeInTheDocument();
  });

  it("stays focused on direct manual runs", async () => {
    renderWithQueryClient(<PlaygroundWorkspace />);

    await waitFor(() => expect(agentApi.listAgents).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalledTimes(1));
    expect(
      await screen.findByText(/Dataset-oriented flows live in Evals and Datasets. Playground stays focused on direct manual runs./)
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Dataset")).toBeInTheDocument();
    expect(screen.getByText(/No dataset attached. Playground will run prompt-only until you select one./)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create eval job" })).not.toBeInTheDocument();

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

  it("hydrates rerun state from query-derived props", async () => {
    renderWithQueryClient(
      <PlaygroundWorkspace
        initialDataset="crm-v2"
        initialAgentId="customer_service"
        initialPrompt="Retry the failed support run."
        initialTags={["rerun", "support"]}
      />
    );

    await waitFor(() => expect(agentApi.listAgents).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalledTimes(1));

    expect(screen.getByDisplayValue("Retry the failed support run.")).toBeInTheDocument();
    expect(screen.getByDisplayValue("rerun, support")).toBeInTheDocument();
    expect(screen.getByDisplayValue("crm-v2")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Customer Service (customer_service)")).toBeInTheDocument();
  });
});
