import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import * as agentApi from "@/src/entities/agent/api";
import * as artifactApi from "@/src/entities/artifact/api";
import * as datasetApi from "@/src/entities/dataset/api";
import * as evalApi from "@/src/entities/eval/api";
import { renderWithQueryClient } from "@/test/setup";
import EvalsWorkspace from "@/src/widgets/evals-workspace/EvalsWorkspace";

vi.mock("@/src/entities/agent/api", () => ({
  listAgents: vi.fn()
}));

vi.mock("@/src/entities/dataset/api", () => ({
  listDatasets: vi.fn()
}));

vi.mock("@/src/entities/artifact/api", () => ({
  exportArtifact: vi.fn(),
  getArtifactDownloadUrl: vi.fn(() => "http://127.0.0.1:8000/api/v1/artifacts/artifact-001")
}));

vi.mock("@/src/entities/eval/api", () => ({
  listEvalJobs: vi.fn(),
  listEvalSamples: vi.fn(),
  createEvalJob: vi.fn()
}));

type MockedApiFn = ReturnType<typeof vi.fn>;

describe("Evals workspace", () => {
  beforeEach(() => {
    (agentApi.listAgents as unknown as MockedApiFn).mockReset();
    (artifactApi.exportArtifact as unknown as MockedApiFn).mockReset();
    (datasetApi.listDatasets as unknown as MockedApiFn).mockReset();
    (evalApi.listEvalJobs as unknown as MockedApiFn).mockReset();
    (evalApi.listEvalSamples as unknown as MockedApiFn).mockReset();
    (evalApi.createEvalJob as unknown as MockedApiFn).mockReset();

    (agentApi.listAgents as unknown as MockedApiFn).mockResolvedValue([
      {
        agentId: "basic",
        name: "Basic",
        description: "Minimal smoke agent.",
        framework: "openai-agents-sdk",
        entrypoint: "app.agent_plugins.basic:build_agent",
        defaultModel: "gpt-4.1-mini",
        tags: ["example", "smoke"]
      }
    ]);
    (datasetApi.listDatasets as unknown as MockedApiFn).mockResolvedValue([
      {
        name: "crm-v2",
        rows: [
          { sampleId: "sample-pass", input: "alpha", expected: "alpha", tags: [] },
          { sampleId: "sample-runtime", input: "runtime", expected: "runtime", tags: [] }
        ]
      }
    ]);
    (evalApi.listEvalJobs as unknown as MockedApiFn).mockResolvedValue([
      {
        evalJobId: "eval-001",
        agentId: "basic",
        dataset: "crm-v2",
        project: "nightly-regression",
        tags: ["nightly"],
        scoringMode: "exact_match" as const,
        status: "completed" as const,
        sampleCount: 4,
        scoredCount: 3,
        passedCount: 1,
        failedCount: 1,
        unscoredCount: 1,
        runtimeErrorCount: 1,
        passRate: 33.33,
        failureDistribution: { mismatch: 1, provider_call: 1 },
        createdAt: "2026-03-24T00:00:00Z"
      }
    ]);
    (evalApi.listEvalSamples as unknown as MockedApiFn).mockResolvedValue([
      {
        evalJobId: "eval-001",
        datasetSampleId: "sample-pass",
        runId: "run-001",
        judgement: "passed" as const,
        input: "alpha",
        expected: "alpha",
        actual: "alpha",
        failureReason: null,
        errorCode: null,
        tags: []
      },
      {
        evalJobId: "eval-001",
        datasetSampleId: "sample-fail",
        runId: "run-003",
        judgement: "failed" as const,
        input: "beta",
        expected: "beta",
        actual: "not-beta",
        failureReason: "actual output did not exactly match expected output",
        errorCode: "mismatch",
        tags: []
      },
      {
        evalJobId: "eval-001",
        datasetSampleId: "sample-runtime",
        runId: "run-002",
        judgement: "runtime_error" as const,
        input: "runtime",
        expected: "runtime",
        actual: "live execution failed",
        failureReason: "provider authentication failed",
        errorCode: "provider_call",
        tags: []
      }
    ]);
    (artifactApi.exportArtifact as unknown as MockedApiFn).mockResolvedValue({
      artifactId: "artifact-001",
      format: "jsonl",
      runIds: ["run-002"],
      createdAt: "2026-03-24T00:01:00Z",
      path: "/tmp/eval-failures.jsonl",
      sizeBytes: 27
    });
    (evalApi.createEvalJob as unknown as MockedApiFn).mockResolvedValue({
      evalJobId: "eval-002",
      agentId: "basic",
      dataset: "crm-v2",
      project: "evals",
      tags: [],
      scoringMode: "exact_match" as const,
      status: "queued" as const,
      sampleCount: 2,
      scoredCount: 0,
      passedCount: 0,
      failedCount: 0,
      unscoredCount: 0,
      runtimeErrorCount: 0,
      passRate: 0,
      failureDistribution: {},
      createdAt: "2026-03-24T00:00:00Z"
    });
  });

  it("renders aggregated eval metrics, failure samples, and creates a new eval", async () => {
    renderWithQueryClient(<EvalsWorkspace initialAgentId="basic" initialDataset="crm-v2" initialJobId="eval-001" />);

    await waitFor(() => expect(agentApi.listAgents).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(evalApi.listEvalJobs).toHaveBeenCalledTimes(1));

    expect(await screen.findByText("Eval workbench")).toBeInTheDocument();
    expect((await screen.findAllByText("33.33%")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("provider_call").length).toBeGreaterThan(0);
    expect(screen.getByText("sample-fail")).toBeInTheDocument();
    expect(screen.getByText("sample-runtime")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open run run-002" })).toHaveAttribute("href", "/runs/run-002");

    fireEvent.click(screen.getByRole("button", { name: "Create eval job" }));

    await waitFor(() =>
      expect(evalApi.createEvalJob).toHaveBeenCalledWith({
        agentId: "basic",
        dataset: "crm-v2",
        project: "evals",
        tags: [],
        scoringMode: "exact_match"
      })
    );

    expect(await screen.findByText("Created eval job eval-002.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open selected eval" })).toHaveAttribute("href", "/evals?job=eval-002");
  });

  it("exports only the selected failed runs from eval details", async () => {
    renderWithQueryClient(<EvalsWorkspace initialAgentId="basic" initialDataset="crm-v2" initialJobId="eval-001" />);

    expect(await screen.findByText("Eval workbench")).toBeInTheDocument();
    expect(await screen.findByText("2 of 2 failing runs selected for export.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("checkbox", { name: "Select failed run run-003" }));

    await waitFor(() =>
      expect(screen.getByText("1 of 2 failing runs selected for export.")).toBeInTheDocument()
    );

    fireEvent.click(screen.getByRole("button", { name: "Export 1 run as JSONL" }));

    await waitFor(() =>
      expect(artifactApi.exportArtifact).toHaveBeenCalledWith({
        runIds: ["run-002"],
        format: "jsonl"
      })
    );

    expect(await screen.findByText("Exported 1 run as JSONL.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download JSONL" })).toHaveAttribute(
      "href",
      "http://127.0.0.1:8000/api/v1/artifacts/artifact-001"
    );
  });
});
