import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import * as experimentApi from "@/src/entities/experiment/api";
import * as exportApi from "@/src/entities/export/api";
import { renderWithQueryClient } from "@/test/setup";
import ExportsWorkspace from "@/src/widgets/exports-workspace/ExportsWorkspace";

vi.mock("@/src/entities/experiment/api", () => ({
  listExperiments: vi.fn(),
  listExperimentRuns: vi.fn(),
  createExperiment: vi.fn(),
  startExperiment: vi.fn(),
  cancelExperiment: vi.fn(),
  compareExperiments: vi.fn(),
  patchExperimentRun: vi.fn()
}));

vi.mock("@/src/entities/export/api", () => ({
  listExports: vi.fn(),
  createExport: vi.fn(),
  getExportDownloadUrl: vi.fn((exportId: string) => `http://127.0.0.1:8000/api/v1/exports/${exportId}`)
}));

type MockedApiFn = ReturnType<typeof vi.fn>;

describe("Exports workspace", () => {
  beforeEach(() => {
    (experimentApi.listExperiments as unknown as MockedApiFn).mockReset();
    (experimentApi.listExperimentRuns as unknown as MockedApiFn).mockReset();
    (experimentApi.compareExperiments as unknown as MockedApiFn).mockReset();
    (exportApi.listExports as unknown as MockedApiFn).mockReset();
    (exportApi.createExport as unknown as MockedApiFn).mockReset();

    (experimentApi.listExperiments as unknown as MockedApiFn).mockResolvedValue([
      {
        experimentId: "exp-002",
        name: "candidate",
        datasetName: "crm-v2",
        datasetVersionId: "dataset-v2",
        publishedAgentId: "basic",
        status: "completed",
        tags: ["candidate"],
        scoringMode: "exact_match",
        executorBackend: "k8s-job",
        sampleCount: 2,
        completedCount: 2,
        passedCount: 1,
        failedCount: 1,
        unscoredCount: 0,
        runtimeErrorCount: 0,
        passRate: 0.5,
        failureDistribution: { mismatch: 1 },
        tracing: null,
        errorCode: null,
        errorMessage: null,
        createdAt: "2026-03-25T00:00:00Z"
      }
    ]);
    (experimentApi.listExperimentRuns as unknown as MockedApiFn).mockResolvedValue([
      {
        runId: "run-001",
        experimentId: "exp-002",
        datasetSampleId: "sample-1",
        judgement: "failed" as const,
        input: "where is my refund?",
        expected: "policy answer",
        actual: "bad answer",
        runStatus: "failed" as const,
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
        executorBackend: "k8s-job",
        latencyMs: 12,
        toolCalls: 1,
        traceUrl: "http://phoenix.local/trace/run-001"
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
        sourceExperimentId: "exp-002",
        baselineExperimentId: null,
        candidateExperimentId: null,
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
      sourceExperimentId: "exp-002",
      baselineExperimentId: null,
      candidateExperimentId: null,
      filtersSummary: { judgement: ["failed"], slices: ["returns"] }
    });
  });

  it("creates experiment-based exports and renders export history", async () => {
    renderWithQueryClient(<ExportsWorkspace initialExperimentId="exp-002" />);

    expect(await screen.findByRole("heading", { name: "Exports" })).toBeInTheDocument();
    await waitFor(() => expect(experimentApi.listExperiments).toHaveBeenCalled());
    await waitFor(() => expect(experimentApi.listExperimentRuns).toHaveBeenCalledWith("exp-002"));
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
        experimentId: "exp-002",
        baselineExperimentId: null,
        candidateExperimentId: null,
        datasetSampleIds: ["sample-1"],
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

  it("syncs the selected experiment when the page handoff updates the initial experiment id", async () => {
    (experimentApi.listExperiments as unknown as MockedApiFn).mockResolvedValue([
      {
        experimentId: "exp-002",
        name: "candidate",
        datasetName: "crm-v2",
        datasetVersionId: "dataset-v2",
        publishedAgentId: "basic",
        status: "completed",
        tags: ["candidate"],
        scoringMode: "exact_match",
        executorBackend: "k8s-job",
        sampleCount: 2,
        completedCount: 2,
        passedCount: 1,
        failedCount: 1,
        unscoredCount: 0,
        runtimeErrorCount: 0,
        passRate: 0.5,
        failureDistribution: { mismatch: 1 },
        tracing: null,
        errorCode: null,
        errorMessage: null,
        createdAt: "2026-03-25T00:00:00Z"
      },
      {
        experimentId: "exp-003",
        name: "follow-up",
        datasetName: "returns-v3",
        datasetVersionId: "dataset-v3",
        publishedAgentId: "basic",
        status: "completed",
        tags: ["follow-up"],
        scoringMode: "exact_match",
        executorBackend: "k8s-job",
        sampleCount: 1,
        completedCount: 1,
        passedCount: 1,
        failedCount: 0,
        unscoredCount: 0,
        runtimeErrorCount: 0,
        passRate: 1,
        failureDistribution: {},
        tracing: null,
        errorCode: null,
        errorMessage: null,
        createdAt: "2026-03-26T00:00:00Z"
      }
    ]);

    const view = renderWithQueryClient(<ExportsWorkspace initialExperimentId="exp-002" />);

    const experimentSelect = await screen.findByRole("combobox", { name: "Experiment" });
    await waitFor(() => expect(experimentSelect).toHaveValue("exp-002"));

    view.rerender(<ExportsWorkspace initialExperimentId="exp-003" />);

    await waitFor(() => expect(experimentSelect).toHaveValue("exp-003"));
  });
});
