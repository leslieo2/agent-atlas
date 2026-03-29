import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import * as evalApi from "@/src/entities/eval/api";
import * as exportApi from "@/src/entities/export/api";
import { renderWithQueryClient } from "@/test/setup";
import ExportsWorkspace from "@/src/widgets/exports-workspace/ExportsWorkspace";

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

describe("Exports workspace", () => {
  beforeEach(() => {
    (evalApi.listEvalJobs as unknown as MockedApiFn).mockReset();
    (evalApi.listEvalSamples as unknown as MockedApiFn).mockReset();
    (exportApi.listExports as unknown as MockedApiFn).mockReset();
    (exportApi.createExport as unknown as MockedApiFn).mockReset();

    (evalApi.listEvalJobs as unknown as MockedApiFn).mockResolvedValue([
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
        createdAt: "2026-03-25T00:00:00Z"
      }
    ]);
    (evalApi.listEvalSamples as unknown as MockedApiFn).mockResolvedValue([
      {
        evalJobId: "eval-002",
        datasetSampleId: "sample-1",
        runId: "run-001",
        judgement: "failed" as const,
        input: "where is my refund?",
        expected: "policy answer",
        actual: "bad answer",
        compareOutcome: null,
        failureReason: "mismatch",
        errorCode: "mismatch",
        errorMessage: "answer mismatch",
        tags: ["refund"],
        slice: "returns",
        source: "crm",
        exportEligible: true,
        curationStatus: "review" as const,
        curationNote: null,
        publishedAgentSnapshot: null,
        artifactRef: "source://basic@fp-123",
        imageRef: null,
        runnerBackend: "local-process",
        latencyMs: 12,
        toolCalls: 1,
        phoenixTraceUrl: "http://phoenix.local/trace/run-001"
      }
    ]);
    (exportApi.listExports as unknown as MockedApiFn).mockResolvedValue([
      {
        exportId: "export-history-001",
        format: "jsonl",
        createdAt: "2026-03-25T00:05:00Z",
        path: "/tmp/export-history-001.jsonl",
        sizeBytes: 256,
        rowCount: 3,
        sourceEvalJobId: "eval-002",
        baselineEvalJobId: null,
        candidateEvalJobId: null,
        filtersSummary: { judgement: ["failed"] }
      }
    ]);
    (exportApi.createExport as unknown as MockedApiFn).mockResolvedValue({
      exportId: "export-001",
      format: "parquet",
      createdAt: "2026-03-25T00:10:00Z",
      path: "/tmp/export-001.parquet",
      sizeBytes: 512,
      rowCount: 1,
      sourceEvalJobId: "eval-002",
      baselineEvalJobId: null,
      candidateEvalJobId: null,
      filtersSummary: { judgement: ["failed"], slices: ["returns"] }
    });
  });

  it("creates eval-based exports and renders export history", async () => {
    renderWithQueryClient(<ExportsWorkspace initialEvalJobId="eval-002" />);

    expect(await screen.findByRole("heading", { name: "Exports" })).toBeInTheDocument();
    await waitFor(() => expect(evalApi.listEvalJobs).toHaveBeenCalled());
    await waitFor(() => expect(exportApi.listExports).toHaveBeenCalled());
    expect(screen.getByText("export-history-001")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download" })).toHaveAttribute(
      "href",
      "http://127.0.0.1:8000/api/v1/exports/export-history-001"
    );

    fireEvent.change(screen.getByLabelText("Judgement"), { target: { value: "failed" } });
    fireEvent.change(screen.getByLabelText("Slice"), { target: { value: "returns" } });
    fireEvent.change(screen.getByLabelText("Format"), { target: { value: "parquet" } });
    fireEvent.click(screen.getByRole("button", { name: "Create export" }));

    await waitFor(() =>
      expect(exportApi.createExport).toHaveBeenCalledWith({
        evalJobId: "eval-002",
        baselineEvalJobId: null,
        candidateEvalJobId: null,
        judgements: ["failed"],
        errorCodes: null,
        compareOutcomes: null,
        tags: null,
        slices: ["returns"],
        curationStatuses: null,
        exportEligible: true,
        format: "parquet"
      })
    );

    expect(await screen.findByText(/Created export export-001\./)).toBeInTheDocument();
  });
});
