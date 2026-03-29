import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import * as agentApi from "@/src/entities/agent/api";
import * as datasetApi from "@/src/entities/dataset/api";
import * as evalApi from "@/src/entities/eval/api";
import * as exportApi from "@/src/entities/export/api";
import { renderWithQueryClient } from "@/test/setup";
import EvalsWorkspace from "@/src/widgets/evals-workspace/EvalsWorkspace";

vi.mock("@/src/entities/agent/api", () => ({
  listAgents: vi.fn()
}));

vi.mock("@/src/entities/dataset/api", () => ({
  listDatasets: vi.fn()
}));

vi.mock("@/src/entities/eval/api", () => ({
  listEvalJobs: vi.fn(),
  listEvalSamples: vi.fn(),
  createEvalJob: vi.fn(),
  compareEvalJobs: vi.fn(),
  patchEvalSample: vi.fn()
}));

vi.mock("@/src/entities/export/api", () => ({
  listExports: vi.fn(),
  createExport: vi.fn(),
  getExportDownloadUrl: vi.fn((exportId: string) => `http://127.0.0.1:8000/api/v1/exports/${exportId}`)
}));

type MockedApiFn = ReturnType<typeof vi.fn>;

describe("Evals workspace", () => {
  beforeEach(() => {
    const samples: Array<{
      evalJobId: string;
      datasetSampleId: string;
      runId: string;
      judgement: "passed" | "failed";
      input: string;
      expected: string;
      actual: string;
      compareOutcome: null;
      failureReason: string | null;
      errorCode: string | null;
      errorMessage: string | null;
      tags: string[];
      slice: string;
      source: string;
      exportEligible: boolean;
      curationStatus: "include" | "exclude" | "review";
      curationNote: null;
      publishedAgentSnapshot: null;
      artifactRef: string;
      imageRef: null;
      runnerBackend: string;
      latencyMs: number;
      toolCalls: number;
      phoenixTraceUrl: string;
    }> = [
      {
        evalJobId: "eval-002",
        datasetSampleId: "sample-pass",
        runId: "run-001",
        judgement: "passed" as const,
        input: "alpha",
        expected: "alpha",
        actual: "alpha",
        compareOutcome: null,
        failureReason: null,
        errorCode: null,
        errorMessage: null,
        tags: ["shipping"],
        slice: "shipping",
        source: "crm",
        exportEligible: true,
        curationStatus: "include" as const,
        curationNote: null,
        publishedAgentSnapshot: null,
        artifactRef: "source://basic@fp-123",
        imageRef: null,
        runnerBackend: "local-process",
        latencyMs: 12,
        toolCalls: 1,
        phoenixTraceUrl: "http://phoenix.local/trace/run-001"
      },
      {
        evalJobId: "eval-002",
        datasetSampleId: "sample-regressed",
        runId: "run-002",
        judgement: "failed" as const,
        input: "beta",
        expected: "beta",
        actual: "not-beta",
        compareOutcome: null,
        failureReason: "actual output did not exactly match expected output",
        errorCode: "mismatch",
        errorMessage: "model mismatch",
        tags: ["returns"],
        slice: "returns",
        source: "crm",
        exportEligible: true,
        curationStatus: "review" as const,
        curationNote: null,
        publishedAgentSnapshot: null,
        artifactRef: "source://basic@fp-123",
        imageRef: null,
        runnerBackend: "local-process",
        latencyMs: 15,
        toolCalls: 2,
        phoenixTraceUrl: "http://phoenix.local/trace/run-002"
      }
    ];

    (agentApi.listAgents as unknown as MockedApiFn).mockReset();
    (datasetApi.listDatasets as unknown as MockedApiFn).mockReset();
    (evalApi.listEvalJobs as unknown as MockedApiFn).mockReset();
    (evalApi.listEvalSamples as unknown as MockedApiFn).mockReset();
    (evalApi.createEvalJob as unknown as MockedApiFn).mockReset();
    (evalApi.compareEvalJobs as unknown as MockedApiFn).mockReset();
    (evalApi.patchEvalSample as unknown as MockedApiFn).mockReset();
    (exportApi.createExport as unknown as MockedApiFn).mockReset();
    (exportApi.listExports as unknown as MockedApiFn).mockReset();

    (agentApi.listAgents as unknown as MockedApiFn).mockResolvedValue([
      {
        agentId: "basic",
        name: "Basic",
        description: "Minimal smoke agent.",
        framework: "openai-agents-sdk",
        entrypoint: "app.agent_plugins.basic:build_agent",
        defaultModel: "gpt-5.4-mini",
        tags: ["example", "smoke"]
      }
    ]);
    (datasetApi.listDatasets as unknown as MockedApiFn).mockResolvedValue([
      {
        name: "crm-v2",
        description: "Support data",
        source: "crm",
        version: "2026-03",
        createdAt: "2026-03-24T00:00:00Z",
        rows: []
      }
    ]);
    (evalApi.listEvalJobs as unknown as MockedApiFn).mockResolvedValue([
      {
        evalJobId: "eval-001",
        agentId: "basic-v1",
        dataset: "crm-v2",
        project: "rl-eval",
        tags: ["baseline"],
        scoringMode: "exact_match" as const,
        status: "completed" as const,
        sampleCount: 2,
        scoredCount: 2,
        passedCount: 2,
        failedCount: 0,
        unscoredCount: 0,
        runtimeErrorCount: 0,
        passRate: 100,
        failureDistribution: {},
        createdAt: "2026-03-24T00:00:00Z"
      },
      {
        evalJobId: "eval-002",
        agentId: "basic",
        dataset: "crm-v2",
        project: "rl-eval",
        tags: ["candidate"],
        scoringMode: "exact_match" as const,
        status: "completed" as const,
        sampleCount: 2,
        scoredCount: 2,
        passedCount: 1,
        failedCount: 1,
        unscoredCount: 0,
        runtimeErrorCount: 0,
        passRate: 50,
        failureDistribution: { mismatch: 1 },
        observability: { backend: "phoenix", projectUrl: "http://phoenix.local/project/job/eval-002" },
        createdAt: "2026-03-25T00:00:00Z"
      }
    ]);
    (evalApi.listEvalSamples as unknown as MockedApiFn).mockImplementation(async () => samples);
    (evalApi.compareEvalJobs as unknown as MockedApiFn).mockResolvedValue({
      baselineEvalJobId: "eval-001",
      candidateEvalJobId: "eval-002",
      dataset: "crm-v2",
      distribution: { improved: 0, regressed: 1, unchanged_pass: 1 },
      samples: [
        {
          datasetSampleId: "sample-pass",
          baselineJudgement: "passed",
          candidateJudgement: "passed",
          compareOutcome: "unchanged_pass",
          errorCode: null,
          slice: "shipping",
          tags: ["shipping"],
          candidateRunSummary: { runId: "run-001", actual: "alpha", traceUrl: "http://phoenix.local/trace/run-001" }
        },
        {
          datasetSampleId: "sample-regressed",
          baselineJudgement: "passed",
          candidateJudgement: "failed",
          compareOutcome: "regressed",
          errorCode: "mismatch",
          slice: "returns",
          tags: ["returns"],
          candidateRunSummary: { runId: "run-002", actual: "not-beta", traceUrl: "http://phoenix.local/trace/run-002" }
        }
      ]
    });
    (evalApi.patchEvalSample as unknown as MockedApiFn).mockImplementation(
      async (_evalJobId: string, datasetSampleId: string, payload: { curationStatus?: "include" | "exclude" | "review"; exportEligible?: boolean }) => {
        const sample = samples.find((item) => item.datasetSampleId === datasetSampleId)!;
        sample.curationStatus = payload.curationStatus ?? sample.curationStatus;
        sample.exportEligible = payload.exportEligible ?? sample.exportEligible;
        return sample;
      }
    );
    (evalApi.createEvalJob as unknown as MockedApiFn).mockResolvedValue({
      evalJobId: "eval-003",
      agentId: "basic",
      dataset: "crm-v2",
      project: "rl-eval",
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
      createdAt: "2026-03-25T00:30:00Z"
    });
    (exportApi.createExport as unknown as MockedApiFn).mockResolvedValue({
      exportId: "export-001",
      format: "jsonl",
      createdAt: "2026-03-25T00:40:00Z",
      path: "/tmp/export-001.jsonl",
      sizeBytes: 128,
      rowCount: 2,
      sourceEvalJobId: "eval-002",
      baselineEvalJobId: "eval-001",
      candidateEvalJobId: "eval-002",
      filtersSummary: {}
    });
    (exportApi.listExports as unknown as MockedApiFn).mockResolvedValue([]);
  });

  it("creates eval jobs, compares baseline and candidate samples, patches curation, and exports filtered rows", async () => {
    renderWithQueryClient(<EvalsWorkspace initialAgentId="basic" initialDataset="crm-v2" initialJobId="eval-002" />);

    expect(await screen.findByRole("heading", { name: "Evals" })).toBeInTheDocument();
    await waitFor(() => expect(evalApi.listEvalJobs).toHaveBeenCalled());
    await waitFor(() => expect(evalApi.listEvalSamples).toHaveBeenCalled());
    await waitFor(() => expect(evalApi.compareEvalJobs).toHaveBeenCalled());

    expect(screen.getByRole("link", { name: "Open Phoenix job view" })).toHaveAttribute(
      "href",
      "http://phoenix.local/project/job/eval-002"
    );
    expect(await screen.findByText("sample-regressed")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Exclude" })[0]);
    await waitFor(() =>
      expect(evalApi.patchEvalSample).toHaveBeenCalledWith("eval-002", "sample-pass", {
        curationStatus: "exclude",
        curationNote: null,
        exportEligible: true
      })
    );

    fireEvent.change(screen.getByLabelText("Compare outcome"), { target: { value: "regressed" } });
    fireEvent.click(screen.getByRole("button", { name: /Export JSONL/i }));
    await waitFor(() =>
      expect(exportApi.createExport).toHaveBeenCalledWith({
        evalJobId: null,
        baselineEvalJobId: "eval-001",
        candidateEvalJobId: "eval-002",
        datasetSampleIds: ["sample-regressed"],
        judgements: null,
        errorCodes: null,
        compareOutcomes: ["regressed"],
        tags: null,
        slices: null,
        curationStatuses: null,
        format: "jsonl"
      })
    );

    expect(await screen.findByText(/Created JSONL export export-001\./)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download export" })).toHaveAttribute(
      "href",
      "http://127.0.0.1:8000/api/v1/exports/export-001"
    );

    fireEvent.click(screen.getByRole("button", { name: "Create eval job" }));
    await waitFor(() =>
      expect(evalApi.createEvalJob).toHaveBeenCalledWith({
        agentId: "basic",
        dataset: "crm-v2",
        scoringMode: "exact_match",
        tags: []
      })
    );
  });
});
